"""Mechanical repair engine for closing the verification -> revision loop.

This engine performs MECHANICAL repairs only. Semantic prose revision,
anti-cliché rewriting, and hedging-copy decisions are the LLM Auditor's domain
in the authoritative /makewiki path. Python never exercises semantic judgment
here: every repair is driven by verification evidence (grounding / codebase /
cross-language parity) and applied as an exact, deterministic transformation.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReview
from makewiki_skills.verification.code_grounding_verifier import GroundingReport
from makewiki_skills.verification.codebase_verifier import CodebaseVerificationReport

# Canonical mechanical-only action vocabulary. Semantic actions (``anti_cliche``,
# narrative ``hedge_ungrounded`` prose) are intentionally absent — those are the
# LLM Auditor's job in the authoritative /makewiki flow.
CANONICAL_ACTION_TYPES = frozenset(
    {
        "harmonize_code_block",  # cross-language code parity by stable ID
        "hedge_ungrounded",  # evidence-driven UNKNOWN caveat for ungrounded commands
        "link_fix",  # mechanical link correction (reserved, evidence-gated)
        "format_normalize",  # mechanical formatting normalization (reserved)
    }
)


@dataclass
class RevisionAction:
    action_type: str  # one of CANONICAL_ACTION_TYPES
    file_slug: str
    language: str
    description: str


@dataclass
class RevisionReport:
    round_number: int = 0
    issues_before: int = 0
    issues_after: int = 0
    total_actions: int = 0
    attempted_fixes: int = 0
    verified_resolutions: int = 0
    introduced_regressions: int = 0
    actions: list[RevisionAction] = field(default_factory=list)


class MechanicalRepairEngine:
    """Consumes verification and review reports to apply mechanical repairs.

    This engine performs MECHANICAL repairs only. Semantic prose revision,
    anti-cliché rewriting, and hedging-copy decisions are the LLM Auditor's
    domain in the authoritative /makewiki path.
    """

    def __init__(
        self,
        auto_hedge: bool = True,
        auto_harmonize: bool = True,
        legacy_anti_cliche: bool = False,
    ) -> None:
        self.auto_hedge = auto_hedge
        self.auto_harmonize = auto_harmonize
        self.legacy_anti_cliche = legacy_anti_cliche

    def revise(
        self,
        documents: dict[str, list[GeneratedDocument]],
        grounding_report: GroundingReport | None = None,
        codebase_report: CodebaseVerificationReport | None = None,
        cross_language_report: CrossLanguageReview | None = None,
    ) -> tuple[dict[str, list[GeneratedDocument]], RevisionReport]:
        """Apply mechanical repairs to generated documents based on verification findings.

        No semantic prose rewriting happens here. The only text this engine
        injects is either (a) a canned UNKNOWN evidence caveat for commands the
        verifier proved ungrounded, or (b) byte-exact code blocks harmonized
        across languages by stable block ID.
        """
        report = RevisionReport()
        revised_docs: dict[str, list[GeneratedDocument]] = {}

        # Clone documents so repair is side-effect free.
        for lang, doc_list in documents.items():
            revised_docs[lang] = [
                GeneratedDocument(
                    filename=doc.filename,
                    base_name=doc.base_name,
                    language_code=doc.language_code,
                    content=doc.content,
                    word_count=doc.word_count,
                    generation_timestamp=doc.generation_timestamp,
                )
                for doc in doc_list
            ]

        # Legacy scaffold-only anti-cliché rewrite. NEVER runs in the normal
        # repair loop: it only activates when the engine is explicitly
        # constructed with ``legacy_anti_cliche=True`` for the legacy scaffold.
        if self.legacy_anti_cliche:
            for lang, doc_list in revised_docs.items():
                for doc in doc_list:
                    cleaned_content, count = self._legacy_anti_cliche_cleanup(doc.content, lang)
                    if count > 0:
                        doc.content = cleaned_content
                        report.actions.append(
                            RevisionAction(
                                action_type="format_normalize",
                                file_slug=doc.filename,
                                language=lang,
                                description=f"Legacy scaffold cleanup: normalized {count} phrasing artifact(s)",
                            )
                        )

        # 1. Code grounding & codebase verification: insert canned UNKNOWN
        #    evidence caveats for commands the verifier proved ungrounded.
        if self.auto_hedge and (grounding_report or codebase_report):
            ungrounded_commands: set[str] = set()
            if grounding_report:
                for v in grounding_report.violations:
                    if v.claim.claim_type == "command":
                        ungrounded_commands.add(v.claim.claim_text)
            if codebase_report:
                for check in codebase_report.checks:
                    if not check.verified and check.claim_type == "command":
                        ungrounded_commands.add(check.claim_text)

            if ungrounded_commands:
                for lang, doc_list in revised_docs.items():
                    for doc in doc_list:
                        new_content, count = self._hedge_ungrounded_commands(
                            doc.content, ungrounded_commands, lang
                        )
                        if count > 0:
                            doc.content = new_content
                            report.actions.append(
                                RevisionAction(
                                    action_type="hedge_ungrounded",
                                    file_slug=doc.filename,
                                    language=lang,
                                    description=(
                                        f"Attached UNKNOWN evidence caveat for {count} ungrounded command(s)"
                                    ),
                                )
                            )

        # 2. Cross-language code parity harmonization by stable block ID.
        if self.auto_harmonize and cross_language_report and len(revised_docs) >= 2:
            harmonized_count = self._harmonize_cross_language_code(revised_docs)
            if harmonized_count > 0:
                report.actions.append(
                    RevisionAction(
                        action_type="harmonize_code_block",
                        file_slug="all",
                        language="all",
                        description=f"Harmonized {harmonized_count} cross-language code block(s) by stable ID",
                    )
                )

        report.total_actions = len(report.actions)
        report.attempted_fixes = len(report.actions)
        return revised_docs, report

    # ------------------------------------------------------------------
    # Legacy scaffold helper (NOT part of the authoritative flow)
    # ------------------------------------------------------------------
    def _legacy_anti_cliche_cleanup(self, content: str, lang: str) -> tuple[str, int]:
        """LEGACY scaffold-only prose cleanup.

        This rewrites prose (heading colons, Chinese AI-cliché phrases like
        不仅…更是…). It is exactly the kind of semantic judgment the LLM Auditor
        owns in the authoritative /makewiki path, so it is disabled by default
        (``legacy_anti_cliche=False``) and only used by the legacy scaffold.
        """
        changes = 0
        lines = content.splitlines()
        new_lines: list[str] = []

        for line in lines:
            original_line = line
            # Clean colons in Markdown headings (e.g. ## 步骤 1：安装 -> ## 步骤 1 安装)
            if line.startswith("#"):
                line = re.sub(r"(#+\s+[^:：]+)[：:]\s*", r"\1 ", line)

            # Clean Chinese AI cliché constructs
            if lang == "zh-CN" or "zh" in lang:
                line = re.sub(
                    r"不仅(?:仅)?是([^，]+)，更(?:是|为一个)([^。]+)", r"\1，同时提供\2", line
                )
                line = re.sub(r"不是([^，]+)，而是([^。]+)", r"\2", line)
                line = line.replace("赋能", "支持")
                line = line.replace("底层逻辑", "核心机制")

            if line != original_line:
                changes += 1
            new_lines.append(line)

        return "\n".join(new_lines), changes

    # ------------------------------------------------------------------
    # Mechanical: evidence-driven UNKNOWN caveat
    # ------------------------------------------------------------------
    def _hedge_ungrounded_commands(
        self, content: str, ungrounded_commands: set[str], lang: str
    ) -> tuple[str, int]:
        """Attach a fixed, factual UNKNOWN evidence caveat around unverified commands.

        The caveat text is a canned, per-language statement — a pure marker that
        the command could not be mechanically verified against the codebase. It
        is driven entirely by verification evidence and never invents ambiguity
        prose ("may be experimental").
        """
        hedged_count = 0
        caveat_text = (
            "\n> [!NOTE] 这条命令未在当前代码库中找到显式声明，无法机械验证 "
            "(This command could not be mechanically verified against the codebase)."
            if "zh" in lang
            else "\n> [!NOTE] This command could not be mechanically verified against the codebase (UNKNOWN evidence)."
        )

        for cmd in ungrounded_commands:
            if not cmd or len(cmd) < 3:
                continue
            # Look for fenced code blocks containing the ungrounded command
            pattern = re.compile(rf"(```(?:bash|sh|shell|zsh)?\n[^\n]*{re.escape(cmd)}[^\n]*\n```)")
            if pattern.search(content) and caveat_text not in content:
                content = pattern.sub(rf"\1{caveat_text}", content, count=1)
                hedged_count += 1

        return content, hedged_count

    # ------------------------------------------------------------------
    # Mechanical: stable-ID cross-language code block harmonization
    # ------------------------------------------------------------------
    _BLOCK_ID_PATTERN = re.compile(r"\[\[id:([A-Za-z0-9_.\-]+)\]\]")
    _CODE_BLOCK_PATTERN = re.compile(
        r"```(?P<lang>[a-zA-Z0-9_\-\+]*)\n(?P<code>.*?)```", re.DOTALL
    )

    @classmethod
    def _block_id(cls, content: str) -> str | None:
        """Return the stable block ID declared for a fenced code block, if any.

        The ID marker may appear on the line immediately preceding the fence, or
        as the first line inside the fence body (e.g. ``[[id:getting_started.install]]``).
        """
        stripped = content.lstrip()
        # Marker inside the fence body (first line).
        first_inner_line = content.split("\n", 1)[0] if "\n" in content else ""
        match = cls._BLOCK_ID_PATTERN.search(content)
        if match:
            return match.group(1)
        if stripped.startswith("```") and first_inner_line:
            match = cls._BLOCK_ID_PATTERN.search(first_inner_line)
            if match:
                return match.group(1)
        return None

    @classmethod
    def _content_hash(cls, code: str) -> str:
        """Stable (non-cryptographic) hash of a code block body for parity."""
        return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def _extract_blocks_by_id(
        cls, content: str
    ) -> dict[str, tuple[str, str]]:
        """Map each stable block ID to its ``(full_block_text, code_hash)``.

        ``full_block_text`` includes the ID marker line (if it precedes the
        fence) so a dropped/added block can be appended verbatim.
        """
        blocks: dict[str, tuple[str, str]] = {}
        lines = content.splitlines(keepends=True)
        i = 0
        pending_id: str | None = None
        while i < len(lines):
            line = lines[i]
            id_match = cls._BLOCK_ID_PATTERN.search(line)
            if id_match:
                pending_id = id_match.group(1)
                i += 1
                continue
            if line.lstrip().startswith("```") and pending_id is not None:
                # Collect the full fenced block (starting from the marker line).
                block_lines: list[str] = []
                start = i - 1 if (i - 1) >= 0 and cls._BLOCK_ID_PATTERN.search(lines[i - 1]) else i
                if start == i - 1:
                    block_lines.append(lines[i - 1])
                block_lines.append(line)
                j = i + 1
                while j < len(lines) and not lines[j].lstrip().startswith("```"):
                    block_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    block_lines.append(lines[j])
                    j += 1
                full_block = "".join(block_lines)
                code_match = cls._CODE_BLOCK_PATTERN.search(full_block)
                code_body = code_match.group("code") if code_match else ""
                blocks[pending_id] = (full_block, cls._content_hash(code_body))
                i = j
                pending_id = None
                continue
            i += 1
        return blocks

    def _harmonize_cross_language_code(
        self, documents: dict[str, list[GeneratedDocument]]
    ) -> int:
        """Harmonize code blocks across languages by stable block ID.

        Each logical block is matched by its ``[[id:...]]`` marker rather than
        by position. For every ID, if a secondary language is missing the block
        it is appended verbatim from the primary; if a block differs byte-wise
        it is replaced with the primary's exact text. All comparisons are
        mechanical (hash + exact replacement).
        """
        primary_lang = "en" if "en" in documents else next(iter(documents.keys()))
        primary_docs = {d.base_name: d for d in documents[primary_lang]}
        harmonized = 0

        for lang, doc_list in documents.items():
            if lang == primary_lang:
                continue
            for doc in doc_list:
                if doc.base_name not in primary_docs:
                    continue
                primary_doc = primary_docs[doc.base_name]
                primary_blocks = self._extract_blocks_by_id(primary_doc.content)
                doc_blocks = self._extract_blocks_by_id(doc.content)

                if not primary_blocks:
                    continue

                append_blocks: list[str] = []
                replacements: list[tuple[str, str]] = []
                for block_id, (primary_block, primary_hash) in primary_blocks.items():
                    if block_id not in doc_blocks:
                        append_blocks.append(primary_block)
                    else:
                        _, doc_hash = doc_blocks[block_id]
                        if doc_hash != primary_hash:
                            # Replace the secondary's full block (incl. marker)
                            # with the primary's exact text.
                            replacements.append((doc_blocks[block_id][0], primary_block))

                if replacements:
                    new_content = doc.content
                    for old_block, new_block in replacements:
                        if old_block in new_content:
                            new_content = new_content.replace(old_block, new_block)
                            harmonized += 1
                    doc.content = new_content

                if append_blocks:
                    doc.content += "\n\n" + "\n\n".join(append_blocks)
                    harmonized += len(append_blocks)

        return harmonized


# Backwards-compatible alias for the renamed engine. ``RevisionEngine`` was the
# old semantic revision engine; it is now this mechanical-only engine. New code
# should import ``MechanicalRepairEngine`` directly.
RevisionEngine = MechanicalRepairEngine

