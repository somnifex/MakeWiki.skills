"""L1 Existence Verifier: Validate existence of paths, commands, and config keys."""

from __future__ import annotations

import re
from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.toolkit.command_probe import CommandProbeTool
from makewiki_skills.toolkit.config_reader import ConfigReaderTool
from makewiki_skills.toolkit.markdown_tools import MarkdownTool
from makewiki_skills.verification.report import LayerReport, VerificationCheck

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


class L1ExistenceVerifier:
    """Verify that paths, commands, and config keys exist in the repository on disk."""

    def __init__(self, project_dir: Path) -> None:
        self._root = Path(project_dir).resolve()
        self._md = MarkdownTool()
        self._cmd_probe = CommandProbeTool()
        self._cfg_reader = ConfigReaderTool()

        self._real_paths: set[str] | None = None
        self._real_commands: set[str] | None = None
        self._real_config_keys: set[str] | None = None

    def verify_documents(
        self,
        documents: dict[str, list[GeneratedDocument]],
    ) -> LayerReport:
        checks: list[VerificationCheck] = []

        for lang, docs in documents.items():
            for doc in docs:
                facts = self._md.extract_facts(doc.content, lang, doc.filename)
                checks.extend(self._check_paths(doc, facts.file_paths))
                checks.extend(self._check_commands(doc, facts.commands))
                checks.extend(self._check_config_keys(doc, facts.config_keys))

        return LayerReport(
            layer="L1",
            name="Existence",
            checks=checks,
        )

    def _check_paths(
        self,
        doc: GeneratedDocument,
        paths: list[str],
    ) -> list[VerificationCheck]:
        real = self._get_real_paths()
        results: list[VerificationCheck] = []

        for path in paths:
            normalised = path.lstrip("./")
            if normalised in real or path in real:
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="path",
                        claim_text=path,
                        verified=True,
                        status="passed",
                        verification_source="verified_from_repository",
                        detail="File/directory found in repository",
                    )
                )
            elif (self._root / normalised).exists():
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="path",
                        claim_text=path,
                        verified=True,
                        status="passed",
                        verification_source="verified_from_repository",
                        detail="File/directory verified on disk directly",
                    )
                )
            else:
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="path",
                        claim_text=path,
                        verified=False,
                        status="failed",
                        verification_source="verified_from_repository",
                        detail=f"Path '{path}' not found in project repository",
                        suggested_fix=f"Verify that path '{path}' exists or correct the reference",
                    )
                )
        return results

    def _check_commands(
        self,
        doc: GeneratedDocument,
        commands: list[str],
    ) -> list[VerificationCheck]:
        project_cmds = self._get_real_commands()
        results: list[VerificationCheck] = []

        for cmd in commands:
            stripped = cmd.strip()
            if not stripped:
                continue

            # 1. Check generic shell tools
            if any(stripped.startswith(p) for p in _GENERIC_TOOL_PREFIXES):
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="command",
                        claim_text=stripped,
                        verified=True,
                        status="passed",
                        verification_source="generic_shell_semantics",
                        detail="Well-known generic shell tool command",
                    )
                )
                continue

            # 2. Check project script / Makefile target
            if self._command_matches(stripped, project_cmds):
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="command",
                        claim_text=stripped,
                        verified=True,
                        status="passed",
                        verification_source="verified_from_repository",
                        detail="Matches script or target declared in repository",
                    )
                )
                continue

            # 3. Check placeholder command (templates)
            if "<" in stripped and ">" in stripped:
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="command",
                        claim_text=stripped,
                        verified=True,
                        status="passed",
                        verification_source="generic_shell_semantics",
                        detail="Contains placeholder template syntax",
                    )
                )
                continue

            # 4. Check if hedged with uncertainty note
            if self._is_hedged_command(doc.content, stripped):
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="command",
                        claim_text=stripped,
                        verified=True,
                        status="passed",
                        verification_source="hedging_caveat",
                        detail="Hedged with epistemic uncertainty note",
                    )
                )
                continue

            # 5. Unverified command failure
            results.append(
                VerificationCheck(
                    layer="L1",
                    target=doc.filename,
                    language_code=doc.language_code,
                    claim_type="command",
                    claim_text=stripped,
                    verified=False,
                    status="failed",
                    verification_source="verified_from_repository",
                    detail=f"Command '{stripped}' not found in project scripts or Makefile",
                    suggested_fix=f"Declare '{stripped}' in project scripts or add uncertainty caveat",
                )
            )

        return results

    def _check_config_keys(
        self,
        doc: GeneratedDocument,
        keys: list[str],
    ) -> list[VerificationCheck]:
        real_keys = self._get_real_config_keys()
        results: list[VerificationCheck] = []

        for key in keys:
            if key in real_keys:
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="config_key",
                        claim_text=key,
                        verified=True,
                        status="passed",
                        verification_source="verified_from_repository",
                        detail="Found in project configuration files",
                    )
                )
                continue

            if any(rk.endswith(f".{key}") for rk in real_keys):
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="config_key",
                        claim_text=key,
                        verified=True,
                        status="passed",
                        verification_source="verified_from_repository",
                        detail="Matches suffix in project configuration keys",
                    )
                )
                continue

            if re.match(r"^[A-Z][A-Z0-9_]+$", key):
                results.append(
                    VerificationCheck(
                        layer="L1",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="config_key",
                        claim_text=key,
                        verified=True,
                        status="passed",
                        verification_source="generic_shell_semantics",
                        detail="Standard uppercase environment variable pattern",
                    )
                )
                continue

            results.append(
                VerificationCheck(
                    layer="L1",
                    target=doc.filename,
                    language_code=doc.language_code,
                    claim_type="config_key",
                    claim_text=key,
                    verified=False,
                    status="failed",
                    verification_source="verified_from_repository",
                    detail=f"Config key '{key}' not found in project configuration files",
                    suggested_fix=f"Verify '{key}' exists in configuration files",
                )
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
    def _command_matches(claim: str, project_cmds: set[str]) -> bool:
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

    @staticmethod
    def _is_hedged_command(doc_content: str, cmd: str) -> bool:
        if not doc_content or not cmd:
            return False
        pattern = re.compile(
            rf"```(?:bash|sh|shell|zsh)?\s*\n[^\n]*{re.escape(cmd)}[^\n]*\n```\s*\n>\s*\[!NOTE\]",
            re.MULTILINE,
        )
        if pattern.search(doc_content):
            return True
        if "[!NOTE]" in doc_content and (
            "inferred from configuration" in doc_content
            or "未找到显式 AST 声明" in doc_content
            or "experimental" in doc_content
        ):
            block_pattern = re.compile(
                rf"```[^\n]*\n[^\n]*{re.escape(cmd)}[^\n]*\n```",
                re.MULTILINE,
            )
            if block_pattern.search(doc_content):
                return True
        return False
