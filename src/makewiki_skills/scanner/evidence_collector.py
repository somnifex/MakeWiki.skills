"""Collect project facts by reading files, configs, and scripts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.coverage import CoverageReport
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType
from makewiki_skills.toolkit.cli_help_extractor import CLIHelpExtractor
from makewiki_skills.toolkit.command_probe import CommandProbeTool
from makewiki_skills.toolkit.comment_extractor import CommentExtractor
from makewiki_skills.toolkit.config_reader import ConfigReaderTool
from makewiki_skills.toolkit.error_extractor import ErrorStringExtractor
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink, EvidenceTool
from makewiki_skills.toolkit.filesystem import FilesystemTool
from makewiki_skills.toolkit.source_extractor import MultiLanguageSourceExtractor


class CollectedEvidence(BaseModel):
    """Aggregate result of a full evidence collection run."""

    project_dir: str
    detection: ProjectDetectionResult
    facts: list[EvidenceFact] = Field(default_factory=list)
    raw_files_read: list[str] = Field(default_factory=list)
    commands_discovered: list[str] = Field(default_factory=list)
    coverage: CoverageReport = Field(default_factory=CoverageReport)
    collection_timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class EvidenceCollector:
    """Orchestrates evidence gathering across all toolkit tools."""

    def __init__(self, config: MakeWikiConfig) -> None:
        self._config = config
        self._fs = FilesystemTool()
        self._cfg_reader = ConfigReaderTool()
        self._cmd_probe = CommandProbeTool()
        self._evidence = EvidenceTool()
        self._comment_extractor = CommentExtractor()
        self._cli_help_extractor = CLIHelpExtractor()
        self._error_extractor = ErrorStringExtractor()
        self._source_extractor = MultiLanguageSourceExtractor()

    def collect(
        self,
        project_dir: Path,
        detection: ProjectDetectionResult,
    ) -> CollectedEvidence:
        root = Path(project_dir).resolve()
        all_facts: list[EvidenceFact] = []
        files_read: list[str] = []
        commands: list[str] = []

        # Mechanical census: one bounded recursive walk records what exists,
        # what is ignored, and which generated-code boundaries the tool keeps
        # out of the corpus. This is the coverage baseline the LLM Scouts build
        # on — the tool never decides meaning, only presence.
        coverage = CoverageReport()
        self._census(root, coverage)

        all_facts.extend(self._collect_structure(root))

        cfg_facts, cfg_files = self._collect_configs(root, coverage)
        all_facts.extend(cfg_facts)
        files_read.extend(cfg_files)

        doc_facts, doc_files = self._collect_docs(root)
        all_facts.extend(doc_facts)
        files_read.extend(doc_files)

        script_facts, script_cmds = self._collect_scripts(root, detection, coverage)
        all_facts.extend(script_facts)
        commands.extend(script_cmds)

        if self._config.scan.enable_source_intelligence:
            si_facts, si_files = self._collect_source_intelligence(root, detection, coverage)
            all_facts.extend(si_facts)
            files_read.extend(si_files)

        all_facts = EvidenceTool.merge_facts(all_facts)

        coverage.files_inspected_by_tool = sorted(set(files_read))
        coverage.low_confidence_facts = sorted(
            {
                f.claim
                for f in all_facts
                if f.fact_type not in ("path",) and f.best_confidence in ("low", "inferred")
            }
        )

        return CollectedEvidence(
            project_dir=str(root),
            detection=detection,
            facts=all_facts,
            raw_files_read=files_read,
            commands_discovered=commands,
            coverage=coverage,
        )

    # --- categories for the mechanical census ---------------------------------

    _SOURCE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp"}
    _TEST_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"}
    _CONFIG_EXTS = {".yaml", ".yml", ".toml", ".json", ".cfg", ".ini"}
    _MANIFEST_NAMES = {
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "setup.py",
        "setup.cfg",
    }
    _SCRIPT_NAMES = {"Makefile", "CMakeLists.txt", "Taskfile.yml", "Justfile"}
    _DOCKER_NAMES = {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"}
    _GENERATED_DIR_HINTS = {"vendor", "dist", "build", "generated", "third_party"}

    @staticmethod
    def _is_test_path(rel: str) -> bool:
        lowered = rel.lower()
        return (
            "/test" in lowered
            or "/tests" in lowered
            or "/spec" in lowered
            or lowered.startswith("test")
            or "_test" in lowered
            or "test_" in lowered
            or lowered.endswith("_test.go")
        )

    def _census(self, root: Path, coverage: CoverageReport) -> None:
        """One bounded recursive walk recording mechanical coverage facts.

        Records: total non-ignored files (by category), ignored files,
        generated-code boundaries, and a best-effort discovered list. The walk
        is depth- and count-bounded so a pathological tree cannot hang the
        tool; anything beyond the bounds is reported as skipped, not lost.
        """
        ignore_dirs = set(self._config.scan.ignore_dirs)
        max_depth = self._config.scan.max_depth
        max_files = 100_000  # hard iteration ceiling for the census itself

        counts: dict[str, int] = {}
        count = 0
        for path in root.rglob("*"):
            if count >= max_files:
                coverage.files_skipped.append(
                    {"path": "<census ceiling>", "reason": "max_files_cap"}
                )
                break
            count += 1
            rel_path = path.relative_to(root)
            rel = str(rel_path).replace("\\", "/")
            if any(part in ignore_dirs for part in rel_path.parts):
                coverage.ignored_files.append(rel)
                continue
            if not path.is_file():
                continue
            if len(rel_path.parts) > max_depth:
                coverage.files_skipped.append({"path": rel, "reason": "max_depth"})
                continue

            coverage.files_discovered += 1
            category = self._categorize_file(rel)
            counts[category] = counts.get(category, 0) + 1

            if category == "manifest":
                coverage.manifests_found.append(rel)
            if category == "config":
                coverage.configs_found.append(rel)
            if category == "test":
                coverage.tests_inspected.append(rel)

            if self._is_generated_boundary(rel, rel_path):
                coverage.generated_code_boundaries.append(rel)

        coverage.files_by_category = dict(sorted(counts.items()))

    def _categorize_file(self, rel: str) -> str:
        name = rel.rsplit("/", 1)[-1]
        if name in self._MANIFEST_NAMES:
            return "manifest"
        if name in self._DOCKER_NAMES:
            return "infra"
        if name in self._SCRIPT_NAMES:
            return "script"
        if name in (".env", ".env.example"):
            return "config"
        ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
        if name.startswith(".github") or rel.startswith(".github/"):
            return "ci"
        if rel.startswith("migrations") or "/migrations/" in rel:
            return "migration"
        if ext in self._CONFIG_EXTS and name != "package.json":
            return "config"
        if name.startswith("test") or self._is_test_path(rel):
            if ext in self._TEST_EXTS:
                return "test"
        if ext in self._SOURCE_EXTS:
            return "source"
        if ext in (".md", ".rst", ".txt", ".adoc"):
            return "doc"
        return "other"

    def _is_generated_boundary(self, rel: str, rel_path: Path) -> bool:
        if any(part in self._GENERATED_DIR_HINTS for part in rel_path.parts):
            return True
        if rel.endswith("_pb2.py") or rel.endswith("_pb.go") or rel.endswith(".pb.go"):
            return True
        if ".min." in rel and rel.endswith(".js"):
            return True
        return False

    def _collect_structure(self, root: Path) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []
        result = self._fs.list_directory(
            root,
            pattern="*",
            exclude=self._config.scan.ignore_dirs,
        )
        if result.success:
            for p in result.data["paths"]:
                facts.append(
                    EvidenceFact(
                        claim=f"File exists: {p}",
                        fact_type="path",
                        value=p,
                        evidence=[
                            EvidenceLink(
                                source_path=p,
                                raw_text=p,
                                confidence="high",
                                extraction_method="direct_read",
                            )
                        ],
                    )
                )
        return facts

    def _collect_configs(
        self, root: Path, coverage: CoverageReport
    ) -> tuple[list[EvidenceFact], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []
        config_candidates = [
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.json",
            ".env",
            ".env.example",
            "*.cfg",
            "*.ini",
        ]
        # Also probe nested manifests / configs in a monorepo layout so
        # ``packages/*/pyproject.toml`` or ``config/*.toml`` are not silently
        # missed. Depth- and size-bounded by the same caps as the rest of the
        # walk; ``package.json`` is NOT re-read here (scripts keep it).
        nested_candidates = ["**/*.toml", "**/*.yaml", "**/*.yml", "**/*.cfg", "**/*.ini"]
        for pattern in config_candidates + nested_candidates:
            for p in root.glob(pattern):
                rel = str(p.relative_to(root)).replace("\\", "/")
                if self._config.scan.ignore_dirs and any(
                    part in self._config.scan.ignore_dirs for part in p.relative_to(root).parts
                ):
                    continue
                if not p.is_file():
                    continue
                if p.stat().st_size >= self._config.scan.max_file_size_kb * 1024:
                    coverage.files_skipped.append({"path": rel, "reason": "max_size"})
                    continue
                result = self._cfg_reader.read_any(p)
                if result.success and isinstance(result.data, dict):
                    facts.extend(self._evidence.extract_config_keys(result.data, rel))
                    files_read.append(rel)
                    if rel not in coverage.configs_found:
                        coverage.configs_found.append(rel)
        return facts, files_read

    def _collect_docs(self, root: Path) -> tuple[list[EvidenceFact], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []

        # Mode-aware doc patterns
        mode = self._config.scan.mode
        if mode == "quick":
            doc_patterns = ["README.md", "README.rst", "README.txt", "docs/*.md"]
        elif mode in ["standard", "auto"]:
            doc_patterns = [
                "README.md",
                "README.rst",
                "README.txt",
                "CHANGELOG.md",
                "CHANGELOG",
                "CHANGELOG.rst",
                "HISTORY.md",
                "docs/**/*.md",
                "doc/**/*.md",
            ]
        else:  # deep mode
            doc_patterns = [
                "README.md",
                "README.rst",
                "README.txt",
                "CHANGELOG.md",
                "CHANGELOG",
                "CHANGELOG.rst",
                "HISTORY.md",
                "CONTRIBUTING.md",
                "docs/**/*.md",
                "doc/**/*.md",
                "documentation/**/*.md",
            ]

        # When recursive_docs is False, strip the "**" recursion segments so we
        # only walk the top-level docs/ directory.
        if not self._config.scan.recursive_docs:
            doc_patterns = [
                pattern.replace("/**/", "/*/")
                if "/**/" in pattern
                else pattern
                for pattern in doc_patterns
            ]

        for pattern in doc_patterns:
            for p in root.glob(pattern):
                if p.is_file() and p.stat().st_size < self._config.scan.max_file_size_kb * 1024:
                    rel = str(p.relative_to(root)).replace("\\", "/")
                    result = self._fs.read_file(p)
                    if result.success:
                        content = result.data["content"]
                        cmd_facts = self._evidence.extract_commands(content, rel)
                        facts.extend(cmd_facts)
                        table_facts = self._evidence.extract_markdown_tables(content, rel)
                        facts.extend(table_facts)
                        ver = self._evidence.extract_version(content, rel)
                        if ver:
                            facts.append(ver)
                        facts.extend(self._extract_description(content, rel))
                        files_read.append(rel)
        return facts, files_read

    def _collect_scripts(
        self, root: Path, detection: ProjectDetectionResult, coverage: CoverageReport
    ) -> tuple[list[EvidenceFact], list[str]]:
        facts: list[EvidenceFact] = []
        commands: list[str] = []

        result = self._cmd_probe.detect_available_commands(root)
        if result.success:
            for cmd_data in result.data["commands"]:
                name = cmd_data["name"]
                description = cmd_data.get("description")
                commands.append(name)
                facts.append(
                    EvidenceFact(
                        claim=description or f"Available command: {name}",
                        fact_type="command",
                        value=name,
                        evidence=[
                            EvidenceLink(
                                source_path=cmd_data.get("source", ""),
                                raw_text=cmd_data.get("command", ""),
                                confidence="high",
                                extraction_method="direct_read",
                            )
                        ],
                    )
                )
                src = cmd_data.get("source", "")
                if src and src not in coverage.entrypoints_found:
                    coverage.entrypoints_found.append(src)

        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            r = self._cmd_probe.parse_pyproject_scripts(pyproject)
            if r.success:
                for entry in r.data["scripts"]:
                    commands.append(entry["name"])
                    facts.append(
                        EvidenceFact(
                            claim=f"CLI entrypoint: {entry['name']}",
                            fact_type="command",
                            value=entry["name"],
                            evidence=[
                                EvidenceLink(
                                    source_path="pyproject.toml",
                                    raw_text=f"{entry['name']} = {entry['command']}",
                                    confidence="high",
                                    extraction_method="direct_read",
                                )
                            ],
                        )
                    )
                    coverage.entrypoints_found.append(entry["name"])

        return facts, commands

    def _extract_description(self, content: str, source_path: str) -> list[EvidenceFact]:
        # Remove HTML comments
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        lines = content.split("\n")
        paragraph_lines: list[str] = []
        in_paragraph = False
        for line in lines:
            stripped = line.strip()
            # Remove HTML tags like <div>, <p>, <a>, <img>, <details>, etc.
            clean_line = re.sub(r"<[^>]+>", "", stripped).strip()
            if not clean_line:
                if in_paragraph:
                    break
                continue
            if clean_line.startswith("#"):
                if in_paragraph:
                    break
                continue
            if (
                clean_line.startswith("![")
                or clean_line.startswith("[![")
                or clean_line.startswith("[")
            ):
                continue
            if clean_line.startswith(">"):
                clean_line = (
                    clean_line.lstrip("> [!IMPORTANT]")
                    .lstrip("> [!WARNING]")
                    .lstrip("> [!TIP]")
                    .lstrip("> ")
                    .strip()
                )
                if not clean_line:
                    continue

            in_paragraph = True
            paragraph_lines.append(clean_line)

        if paragraph_lines:
            desc = " ".join(paragraph_lines)[:500]
            return [
                EvidenceFact(
                    claim=f"Project description: {desc[:80]}...",
                    fact_type="description",
                    value=desc,
                    evidence=[
                        EvidenceLink(
                            source_path=source_path,
                            raw_text=desc[:200],
                            confidence="medium",
                            extraction_method="pattern_match",
                        )
                    ],
                )
            ]
        return []

    def _source_pass(
        self,
        root: Path,
        glob_pattern: str,
        max_depth: int,
        max_files: int,
        coverage: CoverageReport,
        label: str,
        extractors: list[Any],
        files_read: list[str],
        facts: list[EvidenceFact],
    ) -> None:
        """Shared loop for a single-language source pass.

        ``extractors`` is a list of extractor objects each exposing
        ``extract_from_file(path) -> list[SourceSymbolFact]`` and
        ``to_evidence_facts(facts) -> list[EvidenceFact]`` (paired, so a fact
        type keeps its owning extractor). Applies the same max_depth /
        ignore_dirs / max_size / max_files caps as every pass, and records a
        silent-truncation marker into coverage when max_files stops the walk,
        so the LLM Scout layer sees that ``label`` was only partially
        inspected.
        """
        scanned = 0
        for file in sorted(root.rglob(glob_pattern)):
            rel_path = file.relative_to(root)
            if len(rel_path.parts) > max_depth:
                continue
            rel = str(rel_path).replace("\\", "/")
            if any(part in self._config.scan.ignore_dirs for part in rel_path.parts):
                continue
            if file.stat().st_size > self._config.scan.max_file_size_kb * 1024:
                continue
            if scanned >= max_files:
                coverage.skipped_due_to_max_files += 1
                coverage.uncovered_categories.append(label)
                return
            any_read = False
            for extractor in extractors:
                file_facts = extractor.extract_from_file(file)
                if file_facts:
                    for sf in file_facts:
                        sf.source_path = rel
                    facts.extend(extractor.to_evidence_facts(file_facts))
                    any_read = True
            if any_read and rel not in files_read:
                files_read.append(rel)
            scanned += 1

    def _collect_source_intelligence(
        self, root: Path, detection: ProjectDetectionResult, coverage: CoverageReport
    ) -> tuple[list[EvidenceFact], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []

        # Mode-aware defaults + user override via scan.source_intelligence_max_files.
        mode = self._config.scan.mode
        if mode == "quick":
            max_files = min(self._config.scan.source_intelligence_max_files, 10)
        elif mode in ["standard", "auto"]:
            max_files = self._config.scan.source_intelligence_max_files
        else:  # deep
            max_files = max(self._config.scan.source_intelligence_max_files, 200)

        max_depth = self._config.scan.max_depth

        config_patterns = ["*.yaml", "*.yml", "*.toml", ".env", ".env.example", "*.cfg", "*.ini"]
        for pattern in config_patterns:
            for p in root.glob(pattern):
                if p.is_file() and p.stat().st_size < self._config.scan.max_file_size_kb * 1024:
                    rel = str(p.relative_to(root)).replace("\\", "/")
                    if coverage.configs_found and rel not in coverage.configs_found:
                        coverage.configs_found.append(rel)
                    comments = self._comment_extractor.extract_comments(p)
                    if comments:
                        for c in comments:
                            c.source_path = rel
                        facts.extend(self._comment_extractor.to_evidence_facts(comments))

        # 1. Python source intelligence
        is_python = detection.project_type in (
            ProjectType.PYTHON_CLI,
            ProjectType.PYTHON_LIBRARY,
            ProjectType.PYTHON_SERVICE,
        )
        if is_python:
            self._source_pass(
                root, "*.py", max_depth, max_files, coverage, "python",
                [self._cli_help_extractor, self._error_extractor, self._source_extractor],
                files_read, facts,
            )
        else:
            # Python source exists but project type did not gate the pass.
            if list(root.rglob("*.py")):
                coverage.uncovered_categories.append("python")

        # 2. Go source intelligence (only when Go is present or detected).
        is_go = (
            detection.project_type == ProjectType.GO_CLI
            or list(root.glob("*.go"))
            or list(root.glob("go.mod"))
        )
        if is_go:
            self._source_pass(
                root, "*.go", max_depth, max_files, coverage, "go",
                [self._source_extractor],
                files_read, facts,
            )

        # 3. Rust source intelligence
        is_rust = detection.project_type == ProjectType.RUST_CLI or list(root.glob("Cargo.toml"))
        if is_rust:
            self._source_pass(
                root, "*.rs", max_depth, max_files, coverage, "rust",
                [self._source_extractor],
                files_read, facts,
            )

        # 4. JS/TS source intelligence. Previously JS/TS was never walked by
        # the mechanical plane (a whole ecosystem silently skipped). Hook it in
        # behind the same caps; the extractor surfaces module/export/bins and
        # the coverage report now shows node source counts.
        is_node = detection.project_type in (
            ProjectType.NODE_CLI,
            ProjectType.NODE_REACT,
            ProjectType.NODE_LIBRARY,
        ) or list(root.rglob("*.tsx")) or list(root.rglob("*.ts")) or list(root.rglob("*.js"))
        if is_node:
            self._source_pass(
                root, "*.js", max_depth, max_files, coverage, "javascript",
                [self._source_extractor],
                files_read, facts,
            )
            self._source_pass(
                root, "*.ts", max_depth, max_files, coverage, "typescript",
                [self._source_extractor],
                files_read, facts,
            )

        return facts, files_read
