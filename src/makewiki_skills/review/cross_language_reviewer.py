"""Compare structured facts across language versions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field

from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.toolkit.markdown_tools import FactSet, MarkdownTool

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
    reviewed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
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

class CrossLanguageReviewer:
    """Compare documents across languages for factual consistency.

    Only structured facts are compared: commands, config keys, file paths,
    version strings, and section names. Prose is intentionally ignored.
    """

    def __init__(self) -> None:
        self._md = MarkdownTool()

    def review(
        self, documents: dict[str, list[GeneratedDocument]]
    ) -> CrossLanguageReview:
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
            3 if d.severity == "critical" else 2 if d.severity == "major" else 1
            for d in deltas
        )
        score = max(0.0, 1.0 - penalty / total_checks)

        return CrossLanguageReview(
            languages_reviewed=languages,
            fact_deltas=deltas,
            page_coverage=page_coverage,
            consistency_score=round(score, 3),
        )

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

    def _compare_fact_sets(
        self, sets: list[tuple[str, FactSet]]
    ) -> list[FactDelta]:
        deltas: list[FactDelta] = []

        deltas.extend(
            self._diff_values(
                [(lang, fs.commands) for lang, fs in sets],
                "command",
                "critical",
            )
        )

        deltas.extend(
            self._diff_values(
                [(lang, fs.config_keys) for lang, fs in sets],
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
