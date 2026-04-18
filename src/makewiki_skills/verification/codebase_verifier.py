"""Verify rendered docs against the project files on disk.

Unlike :class:`CodeGroundingVerifier`, this step checks the real
repository instead of the collected evidence cache.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.toolkit.command_probe import CommandProbeTool
from makewiki_skills.toolkit.config_reader import ConfigReaderTool
from makewiki_skills.toolkit.markdown_tools import MarkdownTool


class CodebaseCheck(BaseModel):
    """A single claim checked against the real project filesystem."""

    document: str
    language_code: str
    claim_text: str
    claim_type: Literal["path", "command", "config_key"]
    verified: bool
    detail: str


class CodebaseVerificationReport(BaseModel):
    """Result of verifying generated documents against the actual codebase."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    verified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    checks: list[CodebaseCheck] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.checks if c.verified)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.verified)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> float:
        if not self.checks:
            return 1.0
        return round(self.verified_count / len(self.checks), 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self.failed_count == 0

    def failures(self) -> list[CodebaseCheck]:
        return [c for c in self.checks if not c.verified]


_GENERIC_TOOL_PREFIXES: list[str] = [
    "cd ",
    "mkdir ",
    "git ",
    "pip install",
    "pip3 install",
    "pipx ",
    "uv ",
    "npm install",
    "npm init",
    "npx ",
    "pnpm install",
    "pnpm init",
    "yarn install",
    "yarn add",
    "python ",
    "python3 ",
    "node ",
    "cargo install",
    "go install",
    "brew ",
    "apt ",
    "apt-get ",
    "curl ",
    "wget ",
    "docker ",
    "docker-compose ",
    "sudo ",
]


class CodebaseVerifier:
    """Check rendered document claims against the project filesystem."""

    def __init__(self, project_dir: Path) -> None:
        self._root = Path(project_dir).resolve()
        self._md = MarkdownTool()
        self._cmd_probe = CommandProbeTool()
        self._cfg_reader = ConfigReaderTool()

        self._real_paths: set[str] | None = None
        self._real_commands: set[str] | None = None
        self._real_config_keys: set[str] | None = None

    def verify(
        self,
        documents: dict[str, list[GeneratedDocument]],
    ) -> CodebaseVerificationReport:
        checks: list[CodebaseCheck] = []
        for _lang, docs in documents.items():
            for doc in docs:
                facts = self._md.extract_facts(doc.content, doc.language_code, doc.filename)
                checks.extend(self._check_paths(doc, facts.file_paths))
                checks.extend(self._check_commands(doc, facts.commands))
                checks.extend(self._check_config_keys(doc, facts.config_keys))
        return CodebaseVerificationReport(checks=checks)

    def _check_paths(
        self,
        doc: GeneratedDocument,
        paths: list[str],
    ) -> list[CodebaseCheck]:
        real = self._get_real_paths()
        results: list[CodebaseCheck] = []
        for path in paths:
            normalised = path.lstrip("./")
            if normalised in real or path in real:
                results.append(self._ok(doc, path, "path", "exists on disk"))
            elif (self._root / normalised).exists():
                results.append(self._ok(doc, path, "path", "exists on disk (direct check)"))
            else:
                results.append(self._fail(doc, path, "path", "file/directory not found in project"))
        return results

    def _check_commands(
        self,
        doc: GeneratedDocument,
        commands: list[str],
    ) -> list[CodebaseCheck]:
        project_cmds = self._get_real_commands()
        results: list[CodebaseCheck] = []
        for cmd in commands:
            stripped = cmd.strip()
            if not stripped:
                continue
            if any(stripped.startswith(p) for p in _GENERIC_TOOL_PREFIXES):
                results.append(self._ok(doc, stripped, "command", "well-known tool"))
                continue
            if self._command_matches(stripped, project_cmds):
                results.append(self._ok(doc, stripped, "command", "matches project script"))
                continue
            if "<" in stripped and ">" in stripped:
                results.append(self._ok(doc, stripped, "command", "contains placeholder"))
                continue
            results.append(
                self._fail(doc, stripped, "command", "not found in project scripts"),
            )
        return results

    @staticmethod
    def _command_matches(claim: str, project_cmds: set[str]) -> bool:
        """Return ``True`` when a documented command matches a known command."""
        for known in project_cmds:
            if claim == known:
                return True
            if claim.startswith(known) and (
                len(claim) == len(known) or claim[len(known)] in (" ", "\t")
            ):
                return True
            if known in claim.split()[0:1]:
                return True
        return False

    def _check_config_keys(
        self,
        doc: GeneratedDocument,
        keys: list[str],
    ) -> list[CodebaseCheck]:
        real_keys = self._get_real_config_keys()
        results: list[CodebaseCheck] = []
        for key in keys:
            if key in real_keys:
                results.append(self._ok(doc, key, "config_key", "found in project config"))
                continue
            if any(rk.endswith(f".{key}") for rk in real_keys):
                results.append(self._ok(doc, key, "config_key", "matches config key suffix"))
                continue
            if re.match(r"^[A-Z][A-Z0-9_]+$", key):
                results.append(self._ok(doc, key, "config_key", "env-var naming pattern"))
                continue
            results.append(
                self._fail(doc, key, "config_key", "not found in project config files"),
            )
        return results

    def _get_real_paths(self) -> set[str]:
        if self._real_paths is not None:
            return self._real_paths
        paths: set[str] = set()
        try:
            for p in self._root.rglob("*"):
                rel = str(p.relative_to(self._root)).replace("\\", "/")
                if any(
                    part.startswith(".") or part in ("node_modules", "__pycache__", ".venv", "venv")
                    for part in rel.split("/")
                ):
                    continue
                paths.add(rel)
        except OSError:
            pass
        self._real_paths = paths
        return paths

    def _get_real_commands(self) -> set[str]:
        if self._real_commands is not None:
            return self._real_commands
        cmds: set[str] = set()
        result = self._cmd_probe.detect_available_commands(self._root)
        if result.success:
            for entry in result.data["commands"]:
                cmds.add(entry["name"])
        self._real_commands = cmds
        return cmds

    def _get_real_config_keys(self) -> set[str]:
        if self._real_config_keys is not None:
            return self._real_config_keys
        keys: set[str] = set()
        config_patterns = [
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.json",
            ".env",
            ".env.example",
            "*.cfg",
            "*.ini",
        ]
        for pattern in config_patterns:
            for p in self._root.glob(pattern):
                if not p.is_file() or p.stat().st_size > 512_000:
                    continue
                result = self._cfg_reader.read_any(p)
                if result.success and isinstance(result.data, dict):
                    keys.update(ConfigReaderTool.extract_key_paths(result.data))
        self._real_config_keys = keys
        return keys

    @staticmethod
    def _ok(
        doc: GeneratedDocument,
        claim: str,
        claim_type: Literal["path", "command", "config_key"],
        detail: str,
    ) -> CodebaseCheck:
        return CodebaseCheck(
            document=doc.filename,
            language_code=doc.language_code,
            claim_text=claim,
            claim_type=claim_type,
            verified=True,
            detail=detail,
        )

    @staticmethod
    def _fail(
        doc: GeneratedDocument,
        claim: str,
        claim_type: Literal["path", "command", "config_key"],
        detail: str,
    ) -> CodebaseCheck:
        return CodebaseCheck(
            document=doc.filename,
            language_code=doc.language_code,
            claim_text=claim,
            claim_type=claim_type,
            verified=False,
            detail=detail,
        )
