"""Compare structured facts across language versions."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.review.section_parser import parse_document_sections
from makewiki_skills.toolkit.markdown_tools import FactSet, MarkdownTool

_FENCE_PATTERN = re.compile(r"```[a-zA-Z0-9_\-\+]*\n.*?```", re.DOTALL)
_SECTION_MARKER_STRIP = re.compile(r"<!--\s*makewiki:section=[A-Za-z0-9_.\-]+\s*-->")
_ID_MARKER_STRIP = re.compile(r"\[\[(?:id:[A-Za-z0-9_.\-]+|parity:ignore[^\]]*)\]\]")


def _strip_fences(text: str) -> str:
    """Return ``text`` with fenced code blocks and maker lines removed.

    Used to isolate PROSE for aligned-passage review; code blocks are aligned
    separately by their stable block ID. Marker lines (``[[id:...]]``,
    ``[[parity:ignore...]]`` and section markers) are dropped so they never leak
    into prose output.
    """
    text = _FENCE_PATTERN.sub("", text)
    text = _SECTION_MARKER_STRIP.sub("", text)
    text = _ID_MARKER_STRIP.sub("", text)
    return text.strip()



class FactDelta(BaseModel):
    """An inconsistency found between language versions."""

    fact_type: str  # "command" | "config_key" | "file_path" | "version" | "section"
    value: str
    present_in: list[str] = Field(default_factory=list)
    missing_from: list[str] = Field(default_factory=list)
    severity: str = "minor"  # "critical" | "major" | "minor"


class CrossLanguageReview(BaseModel):
    """Result of a cross-language consistency review."""

    review_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    reviewed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    languages_reviewed: list[str] = Field(default_factory=list)
    fact_deltas: list[FactDelta] = Field(default_factory=list)
    page_coverage: dict[str, list[str]] = Field(default_factory=dict)
    consistency_score: float = 1.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def critical_issues(self) -> list[FactDelta]:
        return [d for d in self.fact_deltas if d.severity == "critical"]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return len(self.critical_issues) == 0


class RevisionInstruction(BaseModel):
    """An instruction for revising a document based on review findings."""

    target_language: str | None = None
    target_document: str | None = None
    issue_type: str  # "missing_fact" | "extra_fact" | "missing_page"
    description: str
    severity: str = "minor"


class AlignedPassage(BaseModel):
    """A passage aligned across languages by STABLE identity, not position.

    Each passage is keyed by a stable document ID (``base_name``) plus a stable
    section ID (``<!-- makewiki:section=<slug> -->``) and/or a stable block ID
    (``[[id:...]]``). ``document_id`` is the document's ``base_name`` — it is
    part of the stable identity namespace, so the same ``section_id`` on two
    different pages never collides. ``section_id`` is always the nearest
    preceding section marker (``""`` when none); ``block_id`` is the
    ``[[id:...]]`` for a code-blocks passage, ``None`` for a prose passage.
    ``texts`` maps each language to that passage's text in that language; a
    language that declares the document but NOT this section/block carries
    ``"missing"`` (an absent passage is itself a semantic-review item for the
    Auditor, never papered over with a different section's content).

    ``review_item_id`` is the single, stable identifier shared with the L4b
    semantic checks and the SemanticAuditBundle (one ID system, not three):
    ``L4b:<document_id>:<section_id>`` for prose, with a ``:block:<block_id>``
    suffix for code passages.

    Python only ALIGNS these passages — it never judges whether the meanings
    match. That semantic judgment is the LLM Auditor's L4b step.
    """

    document_id: str = ""
    section_id: str
    block_id: str | None = None
    languages: list[str] = Field(default_factory=list)
    texts: dict[str, str] = Field(default_factory=dict)

    @property
    def review_item_id(self) -> str:
        if self.block_id is None:
            return f"L4b:{self.document_id}:{self.section_id}"
        return f"L4b:{self.document_id}:{self.section_id}:block:{self.block_id}"


class CrossLanguageReviewer:
    """Compare documents across languages for factual consistency.

    Only structured facts are compared: commands, config keys, file paths,
    version strings, and section names. Prose is intentionally ignored.
    """

    def __init__(self) -> None:
        self._md = MarkdownTool()

    def review(self, documents: dict[str, list[DocumentArtifact]]) -> CrossLanguageReview:
        """Run a full cross-language review.

        Args:
            documents: Mapping of language code to rendered documents.
        """
        languages = sorted(documents.keys())
        if len(languages) < 2:
            return CrossLanguageReview(
                languages_reviewed=languages,
                consistency_score=1.0,
            )

        fact_sets: dict[str, dict[str, FactSet]] = {}
        page_coverage: dict[str, list[str]] = {}

        for lang, docs in documents.items():
            fact_sets[lang] = {}
            page_coverage[lang] = []
            for doc in docs:
                fs = self._md.extract_facts(doc.content, lang, doc.base_name)
                fact_sets[lang][doc.base_name] = fs
                page_coverage[lang].append(doc.base_name)

        deltas: list[FactDelta] = []
        all_base_names: set[str] = set()
        for pages in page_coverage.values():
            all_base_names.update(pages)

        for base_name in sorted(all_base_names):
            present = [lang for lang in languages if base_name in page_coverage.get(lang, [])]
            missing = [lang for lang in languages if lang not in present]
            if missing:
                deltas.append(
                    FactDelta(
                        fact_type="page",
                        value=base_name,
                        present_in=present,
                        missing_from=missing,
                        severity="major",
                    )
                )

        for base_name in sorted(all_base_names):
            page_fact_sets = []
            for lang in languages:
                if base_name in fact_sets.get(lang, {}):
                    page_fact_sets.append((lang, fact_sets[lang][base_name]))

            if len(page_fact_sets) >= 2:
                deltas.extend(self._compare_fact_sets(page_fact_sets))

        total_checks = max(len(deltas) + 10, 1)  # avoid division by zero
        penalty = sum(
            3 if d.severity == "critical" else 2 if d.severity == "major" else 1 for d in deltas
        )
        score = max(0.0, 1.0 - penalty / total_checks)

        return CrossLanguageReview(
            languages_reviewed=languages,
            fact_deltas=deltas,
            page_coverage=page_coverage,
            consistency_score=round(score, 3),
        )

    def align_documents(
        self,
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[AlignedPassage]:
        """Align passages across languages by stable section/block ID.

        **Stable public data contract** (consumed by the orchestrator / CLI for
        ``semantic-review`` and ``parity``):

        ``documents`` maps a language code to its rendered ``DocumentArtifact``s.
        Returns a deterministic list of :class:`AlignedPassage`, ordered by
        sorted ``base_name`` then sorted section/block identity:

        * one **prose** passage per stable ``(document_id, section_id)`` —
          ``block_id is None`` — carrying each language's section text with code
          fences and markers removed; and
        * one **code** passage per stable ``(document_id, section_id, block_id)``
          key, carrying each language's verbatim fenced block.

        Pairing is **document-scoped**: ``document_id`` is the doc's
        ``base_name``, so the same section id on two different pages never
        collides. Within a document, sections pair by the
        ``<!-- makewiki:section=<slug> -->`` marker and blocks by
        ``[[id:...]]`` — never by H2 heading text or heading index — so sections
        may be reordered (and headings reworded) across languages and still
        align. If any language document declares no section markers, code blocks
        fall back to pairing by block ID alone (section key ``""``).

        A language that declares the document but NOT a given section/block
        carries ``texts[lang] = "missing"`` and stays in ``languages`` — an
        absent passage is itself a semantic-review item for the Auditor, never
        filled with a different section's content.

        This method only ALIGNS. It never judges prose or asserts meaning
        equality — L4b (semantic prose parity) stays a pending LLM Auditor step
        in Python.
        """
        # Lazy import avoids a load-time circular dependency: l4_cross_language
        # imports this module at module scope, so we import its pure helpers only
        # when this method is actually called (both modules are loaded by then).
        from makewiki_skills.verification.l4_cross_language import (
            pair_blocks_by_section_id,
        )

        languages = sorted(documents.keys())

        # base_name -> {language_code: content} — the document-scoped universe.
        doc_map: dict[str, dict[str, str]] = {}
        for lang in languages:
            for doc in documents[lang]:
                doc_map.setdefault(doc.base_name, {})[lang] = doc.content

        passages: list[AlignedPassage] = []

        # ---- prose passages keyed by (document_id, section_id) --------------
        for base_name in sorted(doc_map):
            lang_map = doc_map[base_name]
            section_texts: dict[str, dict[str, str]] = {}
            for lang, content in lang_map.items():
                parsed = parse_document_sections(content, document_id=base_name)
                for sec in parsed.sections:
                    section_texts.setdefault(sec.section_id, {})[lang] = _strip_fences(
                        sec.content
                    )
            for section_id in sorted(section_texts):
                texts: dict[str, str] = dict(section_texts[section_id])
                for lang in sorted(lang_map):
                    if lang not in texts:
                        texts[lang] = "missing"
                passages.append(
                    AlignedPassage(
                        document_id=base_name,
                        section_id=section_id,
                        block_id=None,
                        languages=sorted(texts.keys()),
                        texts=texts,
                    )
                )

        # ---- code passages keyed by (document_id, section_id, block_id) -----
        for (document_id, section_id, block_id), lang_refs in sorted(
            pair_blocks_by_section_id(documents).items()
        ):
            block_texts: dict[str, str] = {
                lang: ref.full_block for lang, ref in lang_refs.items()
            }
            for lang in sorted(doc_map.get(document_id, {})):
                if lang not in block_texts:
                    block_texts[lang] = "missing"
            passages.append(
                AlignedPassage(
                    document_id=document_id,
                    section_id=section_id,
                    block_id=block_id,
                    languages=sorted(block_texts.keys()),
                    texts=block_texts,
                )
            )

        return passages

    def aligned_passages(
        self,
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[AlignedPassage]:
        """Alias for :meth:`align_documents` (same stable data contract)."""
        return self.align_documents(documents)

    def generate_revision_instructions(
        self, review: CrossLanguageReview
    ) -> list[RevisionInstruction]:
        instructions: list[RevisionInstruction] = []
        for delta in review.fact_deltas:
            if delta.missing_from:
                for lang in delta.missing_from:
                    instructions.append(
                        RevisionInstruction(
                            target_language=lang,
                            target_document=delta.value if delta.fact_type == "page" else None,
                            issue_type=(
                                "missing_page" if delta.fact_type == "page" else "missing_fact"
                            ),
                            description=(
                                f"{delta.fact_type} '{delta.value}' is present in "
                                f"{delta.present_in} but missing from {lang}"
                            ),
                            severity=delta.severity,
                        )
                    )
        return instructions

    def _compare_fact_sets(self, sets: list[tuple[str, FactSet]]) -> list[FactDelta]:
        deltas: list[FactDelta] = []

        deltas.extend(
            self._diff_values(
                [(lang, fs.commands) for lang, fs in sets],
                "command",
                "critical",
            )
        )

        # Diff only ALL_CAPS env-style config keys. Dotted prose identifiers
        # share the `x.y` shape but are not config keys; L1 keeps them pending.
        deltas.extend(
            self._diff_values(
                [
                    (
                        lang,
                        [k for k in fs.config_keys if re.match(r"^[A-Z][A-Z0-9_]+$", k)],
                    )
                    for lang, fs in sets
                ],
                "config_key",
                "critical",
            )
        )

        deltas.extend(
            self._diff_values(
                [(lang, fs.file_paths) for lang, fs in sets],
                "file_path",
                "major",
            )
        )

        deltas.extend(
            self._diff_values(
                [(lang, fs.version_strings) for lang, fs in sets],
                "version",
                "major",
            )
        )

        return deltas

    @staticmethod
    def _diff_values(
        lang_values: list[tuple[str, list[str]]],
        fact_type: str,
        severity: str,
    ) -> list[FactDelta]:
        all_values: set[str] = set()
        for _, values in lang_values:
            all_values.update(values)

        deltas: list[FactDelta] = []
        for value in sorted(all_values):
            present = [lang for lang, vals in lang_values if value in vals]
            missing = [lang for lang, vals in lang_values if value not in vals]
            if missing:
                deltas.append(
                    FactDelta(
                        fact_type=fact_type,
                        value=value,
                        present_in=present,
                        missing_from=missing,
                        severity=severity,
                    )
                )
        return deltas
