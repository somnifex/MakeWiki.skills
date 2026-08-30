"""L5 Epistemic Verifier: Validate confidence alignment and defensive hedging caveats."""

from __future__ import annotations

import re
from pathlib import Path

from makewiki_skills.model.document_artifact import DocumentArtifact
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
    """Collect epistemic candidates; the LLM Auditor holds the verdict.

    Python can mechanically locate candidates (generic shell commands, commands
    known in the repository, hedged utterances, ungrounded assertions) but it
    cannot adjudicate *epistemic correctness* — whether the confidence a document
    projects matches the actual evidence. Every epistemic claim is therefore
    emitted as a ``pending`` candidate with ``verified=False`` so the layer never
    reports a vacuous ``passed`` on semantics.
    """

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
        documents: dict[str, list[DocumentArtifact]],
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

                    is_generic = any(stripped.startswith(p) for p in _GENERIC_TOOL_PREFIXES)
                    is_repo_cmd = any(
                        stripped.startswith(kc) or kc in stripped for kc in known_cmds
                    )
                    matching_facts = [
                        f for f in self._registry.query(fact_type="command")
                        if f.value and (f.value in stripped or stripped in f.value)
                    ]
                    is_hedged = self._is_hedged(doc.content, stripped)

                    if is_generic:
                        source, text = (
                            "generic_shell_semantics",
                            "generic shell command candidate; epistemic verdict reserved for LLM Auditor",
                        )
                    elif is_repo_cmd:
                        source, text = (
                            "verified_from_repository",
                            "repo command located mechanically; meaning/epistemic verdict reserved for LLM Auditor",
                        )
                    elif matching_facts and is_hedged:
                        source, text = (
                            "hedging_caveat",
                            "evidence-backed command with hedging caveat; epistemic verdict reserved for LLM Auditor",
                        )
                    elif matching_facts:
                        source, text = (
                            "verified_from_repository",
                            "evidence-backed command; epistemic verdict reserved for LLM Auditor",
                        )
                    elif is_hedged:
                        source, text = (
                            "hedging_caveat",
                            "hedged command candidate; epistemic verdict reserved for LLM Auditor",
                        )
                    else:
                        source, text = (
                            "heuristic",
                            "ungrounded command candidate; epistemic verdict reserved for LLM Auditor",
                        )

                    checks.append(
                        VerificationCheck(
                            layer="L5",
                            target=doc.filename,
                            language_code=lang,
                            claim_type="epistemic",
                            claim_text=stripped,
                            verified=False,
                            status="pending",
                            verification_source=source,
                            detail=text,
                        )
                    )

        if not checks:
            # No L5 checks were performed. Emit an honest pending check so the
            # layer reports pending (LLM judgment), never a vacuous pass.
            checks.append(
                VerificationCheck(
                    layer="L5",
                    target="all",
                    language_code="all",
                    claim_type="epistemic",
                    claim_text="Epistemic verification",
                    verified=False,
                    status="pending",
                    verification_source="not_executed",
                    detail="No L5 epistemic checks were performed; layer is pending LLM judgment",
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
