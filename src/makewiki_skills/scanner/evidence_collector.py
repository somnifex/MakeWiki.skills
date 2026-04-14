"""Collect project facts by reading files, configs, and scripts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType
from makewiki_skills.toolkit.cli_help_extractor import CLIHelpExtractor
from makewiki_skills.toolkit.command_probe import CommandProbeTool
from makewiki_skills.toolkit.comment_extractor import CommentExtractor
from makewiki_skills.toolkit.config_reader import ConfigReaderTool
from makewiki_skills.toolkit.error_extractor import ErrorStringExtractor
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink, EvidenceTool
from makewiki_skills.toolkit.filesystem import FilesystemTool

class CollectedEvidence(BaseModel):
    """Aggregate result of a full evidence collection run."""

    project_dir: str
    detection: ProjectDetectionResult
    facts: list[EvidenceFact] = Field(default_factory=list)
    raw_files_read: list[str] = Field(default_factory=list)
    commands_discovered: list[str] = Field(default_factory=list)
    collection_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

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

    def collect(
        self,
        project_dir: Path,
        detection: ProjectDetectionResult,
    ) -> CollectedEvidence:
        root = Path(project_dir).resolve()
        all_facts: list[EvidenceFact] = []
        files_read: list[str] = []
        commands: list[str] = []

        all_facts.extend(self._collect_structure(root))

        cfg_facts, cfg_files = self._collect_configs(root)
        all_facts.extend(cfg_facts)
        files_read.extend(cfg_files)

        doc_facts, doc_files = self._collect_docs(root)
        all_facts.extend(doc_facts)
        files_read.extend(doc_files)

        script_facts, script_cmds = self._collect_scripts(root, detection)
        all_facts.extend(script_facts)
        commands.extend(script_cmds)

        if self._config.scan.enable_source_intelligence:
            si_facts, si_files = self._collect_source_intelligence(root, detection)
            all_facts.extend(si_facts)
            files_read.extend(si_files)

        all_facts = EvidenceTool.merge_facts(all_facts)

        return CollectedEvidence(
            project_dir=str(root),
            detection=detection,
            facts=all_facts,
            raw_files_read=files_read,
            commands_discovered=commands,
        )

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

    def _collect_configs(self, root: Path) -> tuple[list[EvidenceFact], list[str]]:
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
        for pattern in config_candidates:
            for p in root.glob(pattern):
                if p.is_file() and p.stat().st_size < self._config.scan.max_file_size_kb * 1024:
                    rel = str(p.relative_to(root)).replace("\\", "/")
                    result = self._cfg_reader.read_any(p)
                    if result.success and isinstance(result.data, dict):
                        facts.extend(
                            self._evidence.extract_config_keys(result.data, rel)
                        )
                        files_read.append(rel)
        return facts, files_read

    def _collect_docs(self, root: Path) -> tuple[list[EvidenceFact], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []
        doc_patterns = ["README.md", "README.rst", "README.txt", "docs/*.md", "doc/*.md"]
        for pattern in doc_patterns:
            for p in root.glob(pattern):
                if p.is_file() and p.stat().st_size < self._config.scan.max_file_size_kb * 1024:
                    rel = str(p.relative_to(root)).replace("\\", "/")
                    result = self._fs.read_file(p)
                    if result.success:
                        content = result.data["content"]
                        cmd_facts = self._evidence.extract_commands(content, rel)
                        facts.extend(cmd_facts)
                        ver = self._evidence.extract_version(content, rel)
                        if ver:
                            facts.append(ver)
                        facts.extend(self._extract_description(content, rel))
                        files_read.append(rel)
        return facts, files_read

    def _collect_scripts(
        self, root: Path, detection: ProjectDetectionResult
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

        return facts, commands

    def _extract_description(self, content: str, source_path: str) -> list[EvidenceFact]:
        lines = content.split("\n")
        paragraph_lines: list[str] = []
        in_paragraph = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_paragraph:
                    break
                continue
            if stripped.startswith("#"):
                if in_paragraph:
                    break
                continue
            if stripped.startswith("![") or stripped.startswith("[!["):
                continue
            in_paragraph = True
            paragraph_lines.append(stripped)

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

    def _collect_source_intelligence(
        self, root: Path, detection: ProjectDetectionResult
    ) -> tuple[list[EvidenceFact], list[str]]:
        facts: list[EvidenceFact] = []
        files_read: list[str] = []
        max_files = self._config.scan.source_intelligence_max_files

        config_patterns = ["*.yaml", "*.yml", "*.toml", ".env", ".env.example", "*.cfg", "*.ini"]
        for pattern in config_patterns:
            for p in root.glob(pattern):
                if p.is_file() and p.stat().st_size < self._config.scan.max_file_size_kb * 1024:
                    comments = self._comment_extractor.extract_comments(p)
                    if comments:
                        rel = str(p.relative_to(root)).replace("\\", "/")
                        for c in comments:
                            c.source_path = rel
                        facts.extend(self._comment_extractor.to_evidence_facts(comments))


        is_python = detection.project_type in (
            ProjectType.PYTHON_CLI,
            ProjectType.PYTHON_LIBRARY,
            ProjectType.PYTHON_SERVICE,
        )
        if is_python:
            py_files_scanned = 0
            for py_file in sorted(root.rglob("*.py")):
                rel = str(py_file.relative_to(root)).replace("\\", "/")
                if any(part in self._config.scan.ignore_dirs for part in py_file.relative_to(root).parts):
                    continue
                if py_file.stat().st_size > self._config.scan.max_file_size_kb * 1024:
                    continue
                if py_files_scanned >= max_files:
                    break

                cli_help_facts = self._cli_help_extractor.extract_from_file(py_file)
                if cli_help_facts:
                    for f in cli_help_facts:
                        f.source_path = rel
                    facts.extend(self._cli_help_extractor.to_evidence_facts(cli_help_facts))
                    files_read.append(rel)

                error_facts = self._error_extractor.extract_from_file(py_file)
                if error_facts:
                    for f in error_facts:
                        f.source_path = rel
                    facts.extend(self._error_extractor.to_evidence_facts(error_facts))
                    if rel not in files_read:
                        files_read.append(rel)

                py_files_scanned += 1

        return facts, files_read
