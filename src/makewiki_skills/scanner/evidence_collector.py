"""Collect project facts by reading files, configs, and scripts."""

from __future__ import annotations

import fnmatch
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.coverage import CoverageReport, ToolFailureRecord
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


def _pruned_walk(
    root: Path,
    ignore_dirs: set[str],
    max_depth: int = 10,
    pattern: str | None = None,
    pruned: list[str] | None = None,
) -> list[tuple[Path, str]]:
    """Perform a top-down directory walk pruning ignored subtrees in-place.

    Returns a list of (absolute_path, relative_posix_path).

    When ``pruned`` is provided, the relative posix paths of every pruned
    item are appended to it — each ignored directory that is cut off in-place
    (and, when pruning is top-down, each of its enclosing walked dirs) is
    recorded once. This lets callers honestly account for what the walk did
    **not** touch, without guessing.
    """
    results: list[tuple[Path, str]] = []
    root_resolved = root.resolve()
    for dirpath, dirnames, filenames in os.walk(str(root_resolved)):
        current_dir = Path(dirpath)
        try:
            rel_dir = current_dir.relative_to(root_resolved)
            depth = len(rel_dir.parts)
        except ValueError:
            depth = 0

        # Prune ignored directories and depth exceeding max_depth in-place
        kept: list[str] = []
        for d in dirnames:
            if d in ignore_dirs or any(fnmatch.fnmatch(d, ign) for ign in ignore_dirs):
                if pruned is not None:
                    pruned.append((rel_dir / d).as_posix())
                continue
            if depth + 1 > max_depth:
                if pruned is not None:
                    pruned.append((rel_dir / d).as_posix())
                continue
            kept.append(d)
        dirnames[:] = kept

        for f in filenames:
            file_path = current_dir / f
            try:
                rel = str(file_path.relative_to(root_resolved)).replace("\\", "/")
            except ValueError:
                rel = f
            # A file sits one level deeper than its parent directory; a file
            # whose depth would exceed max_depth must not be read.
            if depth + 1 > max_depth:
                if pruned is not None:
                    pruned.append((rel_dir / f).as_posix())
                continue
            if any(part in ignore_dirs for part in Path(rel).parts):
                if pruned is not None:
                    pruned.append(rel)
                continue
            if pattern is None or fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(f, pattern):
                results.append((file_path, rel))
    results.sort(key=lambda item: item[1])
    return results


class EvidenceCollector:
    """Orchestrates evidence gathering across all mechanical toolkit tools."""

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
        files_parsed: set[str] = set()
        commands: list[str] = []

        # Mechanical census
        coverage = CoverageReport()
        # Initialize tool health statuses
        for tool_name in ("config_reader", "source_extractor", "comment_extractor", "cli_help_extractor", "error_extractor", "command_probe"):
            coverage.tool_health[tool_name] = "OK"

        self._census(root, coverage)

        all_facts.extend(self._collect_structure(root))

        cfg_facts, cfg_files, cfg_parsed = self._collect_configs(root, coverage)
        all_facts.extend(cfg_facts)
        files_read.extend(cfg_files)
        files_parsed.update(cfg_parsed)

        doc_facts, doc_files, doc_parsed = self._collect_docs(root, coverage)
        all_facts.extend(doc_facts)
        files_read.extend(doc_files)
        files_parsed.update(doc_parsed)

        script_facts, script_cmds, script_parsed = self._collect_scripts(root, detection, coverage)
        all_facts.extend(script_facts)
        commands.extend(script_cmds)
        files_parsed.update(script_parsed)

        if self._config.scan.enable_source_intelligence:
            si_facts, si_files, si_parsed = self._collect_source_intelligence(root, detection, coverage)
            all_facts.extend(si_facts)
            files_read.extend(si_files)
            files_parsed.update(si_parsed)

        all_facts = EvidenceTool.merge_facts(all_facts)

        unique_files_read = sorted(set(files_read))
        coverage.files_inspected_by_tool = unique_files_read
        coverage.files_read = len(unique_files_read)
        coverage.files_parsed = len(files_parsed)

        # Count files with facts
        fact_sources = {
            link.source_path
            for fact in all_facts
            for link in fact.evidence
            if link.source_path
        }
        coverage.files_with_facts = len(fact_sources)
        # Honest "read" accounting: of the files we actually read this pass,
        # how many were tests / manifests respectively. Categorized with the
        # same classifier the census uses, so `tests_read` <= `tests_discovered`
        # and `manifests_read` <= `manifests_discovered` always hold.
        for rel in unique_files_read:
            category = self._categorize_file(rel)
            if category == "test":
                coverage.tests_read += 1
            elif category == "manifest":
                coverage.manifests_read += 1
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
            raw_files_read=unique_files_read,
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
        """One bounded pruned walk recording mechanical coverage facts."""
        ignore_dirs = set(self._config.scan.ignore_dirs)
        max_depth = self._config.scan.max_depth
        max_files = 100_000

        counts: dict[str, int] = {}
        pruned: list[str] = []
        all_walked = _pruned_walk(root, ignore_dirs, max_depth=max_depth, pruned=pruned)
        coverage.ignored_files = sorted(set(pruned))

        count = 0
        for path, rel in all_walked:
            if count >= max_files:
                coverage.skipped_due_to_max_files += 1
                coverage.files_skipped.append(
                    {"path": "<census ceiling>", "reason": "max_files_cap"}
                )
                break
            count += 1

            if not path.is_file():
                continue

            coverage.files_discovered += 1
            category = self._categorize_file(rel)
            counts[category] = counts.get(category, 0) + 1

            if category == "manifest":
                coverage.manifests_found.append(rel)
                coverage.manifests_discovered += 1
            if category == "config":
                coverage.configs_found.append(rel)
                coverage.configs_discovered += 1
            if category == "test":
                coverage.tests_inspected.append(rel)
                coverage.tests_discovered += 1

            if self._is_generated_boundary(rel, Path(rel)):
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
    ) -> tuple[list[EvidenceFact], list[str], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []
        files_parsed: list[str] = []
        ignore_dirs = set(self._config.scan.ignore_dirs)
        max_depth = self._config.scan.max_depth
        max_size = self._config.scan.max_file_size_kb * 1024

        config_extensions = {".yaml", ".yml", ".toml", ".json", ".cfg", ".ini"}
        all_walked = _pruned_walk(root, ignore_dirs, max_depth=max_depth)

        for p, rel in all_walked:
            # Exclude .github workflows from application configs
            if rel.startswith(".github/") or "/.github/" in rel or any(part == ".github" for part in Path(rel).parts):
                continue
            name = p.name.lower()
            ext = p.suffix.lower()
            if not (ext in config_extensions or name in (".env", ".env.example")):
                continue
            if not p.is_file():
                continue
            if p.stat().st_size >= max_size:
                coverage.files_skipped.append({"path": rel, "reason": "max_size"})
                continue

            try:
                result = self._cfg_reader.read_any(p)
                if result.success and isinstance(result.data, dict):
                    extracted = self._evidence.extract_config_keys(result.data, rel)
                    facts.extend(extracted)
                    files_read.append(rel)
                    files_parsed.append(rel)
                    coverage.configs_read += 1
                    if rel not in coverage.configs_found:
                        coverage.configs_found.append(rel)
                elif not result.success:
                    coverage.tool_failures.append(
                        ToolFailureRecord(
                            extractor="config_reader",
                            source_path=rel,
                            error_type="ConfigParseError",
                            message=result.error or "Unknown config read error",
                        )
                    )
                    coverage.tool_health["config_reader"] = "DEGRADED"
            except Exception as exc:
                coverage.tool_failures.append(
                    ToolFailureRecord(
                        extractor="config_reader",
                        source_path=rel,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
                coverage.tool_health["config_reader"] = "TOOL_ERROR"

        return facts, files_read, files_parsed

    def _collect_docs(
        self, root: Path, coverage: CoverageReport
    ) -> tuple[list[EvidenceFact], list[str], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []
        files_parsed: list[str] = []
        ignore_dirs = set(self._config.scan.ignore_dirs)
        max_depth = self._config.scan.max_depth
        max_size = self._config.scan.max_file_size_kb * 1024

        mode = self._config.scan.mode
        if mode == "quick":
            allowed_names = {"readme.md", "readme.rst", "readme.txt"}
            allowed_dirs = {"docs"}
        elif mode in ["standard", "auto"]:
            allowed_names = {
                "readme.md", "readme.rst", "readme.txt",
                "changelog.md", "changelog", "changelog.rst",
                "history.md"
            }
            allowed_dirs = {"docs", "doc"}
        else:
            allowed_names = {
                "readme.md", "readme.rst", "readme.txt",
                "changelog.md", "changelog", "changelog.rst",
                "history.md", "contributing.md"
            }
            allowed_dirs = {"docs", "doc", "documentation"}

        all_walked = _pruned_walk(root, ignore_dirs, max_depth=max_depth)

        for p, rel in all_walked:
            name_lower = p.name.lower()
            parts = Path(rel).parts
            is_allowed_name = name_lower in allowed_names
            is_in_doc_dir = any(part.lower() in allowed_dirs for part in parts[:-1]) and p.suffix.lower() == ".md"
            if not (is_allowed_name or is_in_doc_dir):
                continue
            if not self._config.scan.recursive_docs and len(parts) > 2:
                continue
            if not p.is_file() or p.stat().st_size >= max_size:
                continue

            try:
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
                    files_parsed.append(rel)
            except Exception as exc:
                coverage.tool_failures.append(
                    ToolFailureRecord(
                        extractor="filesystem_doc",
                        source_path=rel,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
        return facts, files_read, files_parsed

    def _collect_scripts(
        self, root: Path, detection: ProjectDetectionResult, coverage: CoverageReport
    ) -> tuple[list[EvidenceFact], list[str], list[str]]:
        facts: list[EvidenceFact] = []
        commands: list[str] = []
        files_parsed: list[str] = []

        try:
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
                        files_parsed.append(src)
        except Exception as exc:
            coverage.tool_failures.append(
                ToolFailureRecord(
                    extractor="command_probe",
                    source_path="<root>",
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )
            coverage.tool_health["command_probe"] = "TOOL_ERROR"

        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            try:
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
                    files_parsed.append("pyproject.toml")
            except Exception as exc:
                coverage.tool_failures.append(
                    ToolFailureRecord(
                        extractor="command_probe",
                        source_path="pyproject.toml",
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )

        return facts, commands, files_parsed

    def _extract_description(self, content: str, source_path: str) -> list[EvidenceFact]:
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        lines = content.split("\n")
        paragraph_lines: list[str] = []
        in_paragraph = False
        for line in lines:
            stripped = line.strip()
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
        pattern: str,
        max_depth: int,
        max_files: int,
        coverage: CoverageReport,
        label: str,
        extractors: list[Any],
        files_read: list[str],
        facts: list[EvidenceFact],
        files_parsed: list[str],
    ) -> None:
        """Shared loop for a single-language source pass with fail-soft isolation."""
        ignore_dirs = set(self._config.scan.ignore_dirs)
        max_size = self._config.scan.max_file_size_kb * 1024
        all_walked = _pruned_walk(root, ignore_dirs, max_depth=max_depth, pattern=pattern)

        scanned = 0
        for file, rel in all_walked:
            if not file.is_file():
                continue
            if file.stat().st_size > max_size:
                continue
            if scanned >= max_files:
                coverage.skipped_due_to_max_files += 1
                coverage.uncovered_categories.append(label)
                return

            processed = False
            for extractor in extractors:
                extractor_name = getattr(extractor, "name", type(extractor).__name__)
                try:
                    file_facts = extractor.extract_from_file(file)
                    processed = True
                    if file_facts:
                        for sf in file_facts:
                            sf.source_path = rel
                        facts.extend(extractor.to_evidence_facts(file_facts))
                except Exception as exc:
                    coverage.tool_failures.append(
                        ToolFailureRecord(
                            extractor=extractor_name,
                            source_path=rel,
                            error_type=type(exc).__name__,
                            message=str(exc),
                        )
                    )
                    coverage.tool_health[extractor_name] = "TOOL_ERROR"

            # A file whose content was handed to an extractor counts as read;
            # files_with_facts separately tracks which yielded evidence.
            if processed and rel not in files_read:
                files_read.append(rel)
                files_parsed.append(rel)
            scanned += 1

    def _collect_source_intelligence(
        self, root: Path, detection: ProjectDetectionResult, coverage: CoverageReport
    ) -> tuple[list[EvidenceFact], list[str], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []
        files_parsed: list[str] = []

        mode = self._config.scan.mode
        if mode == "quick":
            max_files = min(self._config.scan.source_intelligence_max_files, 10)
        elif mode in ["standard", "auto"]:
            max_files = self._config.scan.source_intelligence_max_files
        else:  # deep
            max_files = max(self._config.scan.source_intelligence_max_files, 200)

        max_depth = self._config.scan.max_depth
        ignore_dirs = set(self._config.scan.ignore_dirs)

        config_patterns = ("*.yaml", "*.yml", "*.toml", ".env", ".env.example", "*.cfg", "*.ini")
        all_walked = _pruned_walk(root, ignore_dirs, max_depth=max_depth)
        for p, rel in all_walked:
            if rel.startswith(".github/") or "/.github/" in rel:
                continue
            if not p.is_file() or p.stat().st_size >= self._config.scan.max_file_size_kb * 1024:
                continue
            if not any(fnmatch.fnmatch(p.name, pat) for pat in config_patterns):
                continue

            try:
                comments = self._comment_extractor.extract_comments(p)
                if comments:
                    for c in comments:
                        c.source_path = rel
                    facts.extend(self._comment_extractor.to_evidence_facts(comments))
                    files_parsed.append(rel)
            except Exception as exc:
                coverage.tool_failures.append(
                    ToolFailureRecord(
                        extractor="comment_extractor",
                        source_path=rel,
                        error_type=type(exc).__name__,
                        message=str(exc),
                    )
                )
                coverage.tool_health["comment_extractor"] = "TOOL_ERROR"

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
                files_read, facts, files_parsed,
            )
        else:
            if any(rel.endswith(".py") for _, rel in all_walked):
                coverage.uncovered_categories.append("python")
                coverage.mechanically_uncovered_ecosystems.append("python")

        # 2. Go source intelligence
        is_go = (
            detection.project_type == ProjectType.GO_CLI
            or any(rel.endswith(".go") or rel == "go.mod" for _, rel in all_walked)
        )
        if is_go:
            self._source_pass(
                root, "*.go", max_depth, max_files, coverage, "go",
                [self._source_extractor],
                files_read, facts, files_parsed,
            )
        elif any(rel.endswith(".go") for _, rel in all_walked):
            coverage.mechanically_uncovered_ecosystems.append("go")

        # 3. Rust source intelligence
        is_rust = detection.project_type == ProjectType.RUST_CLI or any(rel == "Cargo.toml" for _, rel in all_walked)
        if is_rust:
            self._source_pass(
                root, "*.rs", max_depth, max_files, coverage, "rust",
                [self._source_extractor],
                files_read, facts, files_parsed,
            )
        elif any(rel.endswith(".rs") for _, rel in all_walked):
            coverage.mechanically_uncovered_ecosystems.append("rust")

        # 4. JS/TS source intelligence
        is_node = detection.project_type in (
            ProjectType.NODE_CLI,
            ProjectType.NODE_REACT,
            ProjectType.NODE_LIBRARY,
        ) or any(rel.endswith((".js", ".ts", ".tsx", ".jsx")) for _, rel in all_walked)
        if is_node:
            self._source_pass(
                root, "*.js", max_depth, max_files, coverage, "javascript",
                [self._source_extractor],
                files_read, facts, files_parsed,
            )
            self._source_pass(
                root, "*.ts", max_depth, max_files, coverage, "typescript",
                [self._source_extractor],
                files_read, facts, files_parsed,
            )
        else:
            if any(rel.endswith((".js", ".ts", ".tsx", ".jsx")) for _, rel in all_walked):
                coverage.mechanically_uncovered_ecosystems.append("javascript")

        return facts, files_read, files_parsed
