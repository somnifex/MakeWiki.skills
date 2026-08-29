"""Automated revision engine for closing the verification -> revision loop."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReview
from makewiki_skills.verification.code_grounding_verifier import GroundingReport
from makewiki_skills.verification.codebase_verifier import CodebaseVerificationReport


@dataclass
class RevisionAction:
    action_type: str  # "harmonize_code_block" | "hedge_ungrounded" | "anti_cliche" | "link_fix"
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


class RevisionEngine:
    """Consumes verification and review reports to autonomously revise documents."""

    def __init__(self, auto_hedge: bool = True, auto_harmonize: bool = True) -> None:
        self.auto_hedge = auto_hedge
        self.auto_harmonize = auto_harmonize

    def revise(
        self,
        documents: dict[str, list[GeneratedDocument]],
        grounding_report: GroundingReport | None = None,
        codebase_report: CodebaseVerificationReport | None = None,
        cross_language_report: CrossLanguageReview | None = None,
    ) -> tuple[dict[str, list[GeneratedDocument]], RevisionReport]:
        """Apply automated revisions to generated documents based on verification findings."""
        report = RevisionReport()
        revised_docs: dict[str, list[GeneratedDocument]] = {}

        # Clone documents
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

        # 1. Anti-AI-Cliché cleanup across all documents
        for lang, doc_list in revised_docs.items():
            for doc in doc_list:
                cleaned_content, count = self._sanitize_ai_cliches(doc.content, lang)
                if count > 0:
                    doc.content = cleaned_content
                    report.actions.append(
                        RevisionAction(
                            action_type="anti_cliche",
                            file_slug=doc.filename,
                            language=lang,
                            description=f"Rewrote {count} AI cliché phrase(s) and cleaned title colons",
                        )
                    )

        # 2. Code grounding & codebase verification hedging
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
                                    description=f"Attached hedging caveat for {count} ungrounded command(s)",
                                )
                            )

        # 3. Cross-language code parity harmonization
        if self.auto_harmonize and cross_language_report and len(revised_docs) >= 2:
            harmonized_count = self._harmonize_cross_language_code(revised_docs)
            if harmonized_count > 0:
                report.actions.append(
                    RevisionAction(
                        action_type="harmonize_code_block",
                        file_slug="all",
                        language="all",
                        description=f"Harmonized {harmonized_count} cross-language code block(s)",
                    )
                )

        report.total_actions = len(report.actions)
        report.attempted_fixes = len(report.actions)
        return revised_docs, report

    def _sanitize_ai_cliches(self, content: str, lang: str) -> tuple[str, int]:
        """Strip binary antitheses and colon artifacts in titles."""
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

    def _hedge_ungrounded_commands(
        self, content: str, ungrounded_commands: set[str], lang: str
    ) -> tuple[str, int]:
        """Attach defensive hedging caveats around unverified commands."""
        hedged_count = 0
        caveat_text = (
            "\n> [!NOTE]\n> 注意：该命令或参数来自扩展配置推断，在当前代码基中未找到显式 AST 声明。"
            if "zh" in lang
            else "\n> [!NOTE]\n> Note: This command or flag is inferred from configuration and may be experimental."
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

    def _harmonize_cross_language_code(self, documents: dict[str, list[GeneratedDocument]]) -> int:
        """Ensure code block languages and command contents match across versions."""
        primary_lang = "en" if "en" in documents else next(iter(documents.keys()))
        primary_docs = {d.base_name: d for d in documents[primary_lang]}
        harmonized = 0

        code_block_pattern = re.compile(
            r"```(?P<lang>[a-zA-Z0-9_\-\+]*)\n(?P<code>.*?)```", re.DOTALL
        )

        for lang, doc_list in documents.items():
            if lang == primary_lang:
                continue
            for doc in doc_list:
                if doc.base_name not in primary_docs:
                    continue
                primary_doc = primary_docs[doc.base_name]
                primary_blocks = list(code_block_pattern.finditer(primary_doc.content))
                doc_blocks = list(code_block_pattern.finditer(doc.content))

                # If secondary language is missing code blocks present in primary, sync them
                if len(doc_blocks) < len(primary_blocks) and primary_blocks:
                    missing_blocks = primary_blocks[len(doc_blocks) :]
                    doc.content += "\n\n" + "\n\n".join(m.group(0) for m in missing_blocks)
                    harmonized += len(missing_blocks)

        return harmonized
