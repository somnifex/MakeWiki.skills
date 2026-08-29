"""L5 Epistemic Verifier: Validate confidence alignment and defensive hedging caveats."""

from __future__ import annotations

import re
from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.toolkit.command_probe import CommandProbeTool
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


class L5EpistemicVerifier:
    """Verify that unconfirmed or inferred claims carry consistent hedging caveats."""

    def __init__(
        self,
        registry: EvidenceRegistry | None = None,
        project_dir: Path | None = None,
    ) -> None:
        self._registry = registry or EvidenceRegistry()
        self._project_dir = Path(project_dir).resolve() if project_dir else None
        self._md = MarkdownTool()
        self._cmd_probe = CommandProbeTool()
        self._known_commands: set[str] | None = None

    def verify_documents(
        self,
        documents: dict[str, list[GeneratedDocument]],
    ) -> LayerReport:
        checks: list[VerificationCheck] = []
        known_cmds = self._get_known_commands()

        for lang, docs in documents.items():
            for doc in docs:
                facts = self._md.extract_facts(doc.content, lang, doc.filename)

                for cmd in facts.commands:
                    stripped = cmd.strip()
                    if not stripped:
                        continue

                    # 1. Check if it's a generic shell command
                    if any(stripped.startswith(p) for p in _GENERIC_TOOL_PREFIXES):
                        checks.append(
                            VerificationCheck(
                                layer="L5",
                                target=doc.filename,
                                language_code=lang,
                                claim_type="epistemic",
                                claim_text=stripped,
                                verified=True,
                                status="passed",
                                verification_source="generic_shell_semantics",
                                detail="Generic shell command; epistemic grounding satisfied",
                            )
                        )
                        continue

                    # 2. Check if command is known in repository scripts/Makefile
                    if any(stripped.startswith(kc) or kc in stripped for kc in known_cmds):
                        checks.append(
                            VerificationCheck(
                                layer="L5",
                                target=doc.filename,
                                language_code=lang,
                                claim_type="epistemic",
                                claim_text=stripped,
                                verified=True,
                                status="passed",
                                verification_source="verified_from_repository",
                                detail="Repository command verified; epistemic grounding satisfied",
                            )
                        )
                        continue

                    # 3. Check if command has evidence in registry
                    matching_facts = [
                        f for f in self._registry.query(fact_type="command")
                        if f.value and (f.value in stripped or stripped in f.value)
                    ]

                    is_hedged = self._is_hedged(doc.content, stripped)

                    if matching_facts:
                        best_conf = matching_facts[0].best_confidence
                        if best_conf in ("low", "inferred") and not is_hedged:
                            checks.append(
                                VerificationCheck(
                                    layer="L5",
                                    target=doc.filename,
                                    language_code=lang,
                                    claim_type="epistemic",
                                    claim_text=stripped,
                                    verified=False,
                                    status="failed",
                                    verification_source="hedging_caveat",
                                    detail=f"Command '{stripped}' has {best_conf} confidence but lacks epistemic hedging caveat",
                                    suggested_fix="Attach [!NOTE] hedging caveat to this command code block",
                                )
                            )
                        else:
                            checks.append(
                                VerificationCheck(
                                    layer="L5",
                                    target=doc.filename,
                                    language_code=lang,
                                    claim_type="epistemic",
                                    claim_text=stripped,
                                    verified=True,
                                    status="passed",
                                    verification_source="hedging_caveat" if is_hedged else "verified_from_repository",
                                    detail="Properly grounded or hedged",
                                )
                            )
                    else:
                        # Ungrounded command
                        if is_hedged:
                            checks.append(
                                VerificationCheck(
                                    layer="L5",
                                    target=doc.filename,
                                    language_code=lang,
                                    claim_type="epistemic",
                                    claim_text=stripped,
                                    verified=True,
                                    status="passed",
                                    verification_source="hedging_caveat",
                                    detail="Ungrounded command is defensively hedged with uncertainty notice",
                                )
                            )
                        else:
                            checks.append(
                                VerificationCheck(
                                    layer="L5",
                                    target=doc.filename,
                                    language_code=lang,
                                    claim_type="epistemic",
                                    claim_text=stripped,
                                    verified=False,
                                    status="failed",
                                    verification_source="hedging_caveat",
                                    detail=f"Ungrounded command '{stripped}' is asserted without uncertainty caveat",
                                    suggested_fix="Add uncertainty disclaimer or hedging note",
                                )
                            )

        if not checks:
            checks.append(
                VerificationCheck(
                    layer="L5",
                    target="all",
                    language_code="all",
                    claim_type="epistemic",
                    claim_text="Epistemic verification",
                    verified=True,
                    status="passed",
                    verification_source="hedging_caveat",
                    detail="All claims carry proper epistemic grounding",
                )
            )

        return LayerReport(
            layer="L5",
            name="Epistemic",
            checks=checks,
        )

    def _get_known_commands(self) -> set[str]:
        if self._known_commands is not None:
            return self._known_commands
        cmds: set[str] = set()
        if self._project_dir and self._project_dir.is_dir():
            res = self._cmd_probe.detect_available_commands(self._project_dir)
            if res.success:
                for c in res.data["commands"]:
                    cmds.add(c["name"])
        self._known_commands = cmds
        return cmds

    @staticmethod
    def _is_hedged(content: str, cmd: str) -> bool:
        if not content or not cmd:
            return False
        pattern = re.compile(
            rf"```(?:bash|sh|shell|zsh)?\s*\n[^\n]*{re.escape(cmd)}[^\n]*\n```\s*\n>\s*\[!NOTE\]",
            re.MULTILINE,
        )
        if pattern.search(content):
            return True
        if "[!NOTE]" in content and (
            "inferred from configuration" in content
            or "未找到显式 AST 声明" in content
            or "experimental" in content
        ):
            block_pattern = re.compile(
                rf"```[^\n]*\n[^\n]*{re.escape(cmd)}[^\n]*\n```",
                re.MULTILINE,
            )
            if block_pattern.search(content):
                return True
        return False
