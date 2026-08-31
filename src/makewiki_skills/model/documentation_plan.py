"""LLM-authored DocumentationPlan validation model.

The DocumentationPlan is the structured handoff from Documentation Modeling to
Page Planning (``references/v3/ARTIFACT_CONTRACTS`` §6, ``tasks/plan-pages.md``):
it records *which documented intents exist and how they are grouped into pages*
before one PageSpec per page is produced. Every field is authored by the
**Documentation Architect LLM**; Python only validates the schema and serializes.

Python MUST NOT split pages automatically, order navigation, group personas, or
infer pages from filenames — any such cognitive judgment is the Architect's, and
the renderer's physical site tree is NOT decided here (the Integrator later maps
this plan to a ``SitePresentationPlan``; see ``tasks/integrate.md``).

All models use ``extra="forbid"`` so a hand-authored artifact with a typo'd or
unexpected key fails loudly at load time instead of being silently dropped.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from makewiki_skills.model.page_spec import PageSpec

#: Forbid unknown keys. ``populate_by_name`` lets the ``from`` YAML key be read
#: via its ``from_`` attribute, keeping the authored contract's ``relations[].from``
#: verbatim.
_PLAN_CONFIG = ConfigDict(extra="forbid", populate_by_name=True)


class DocumentationSection(BaseModel):
    """A named group of pages under one documented intent / persona set.

    Authored by the Architect; Python never groups pages or assigns personas.
    """

    model_config = _PLAN_CONFIG

    id: str = ""
    title_intent: str = ""
    persona: list[str] = Field(default_factory=list)
    pages: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_writable_section(self) -> DocumentationSection:
        """A section must be a real group, not an empty shell.

        ``id`` / ``title_intent`` must be non-blank and any declared ``pages``
        entries must be non-blank page references. Python only checks this
        structural completeness — it never decides which pages belong in a
        section or what the section means (that is the Architect's judgment).
        """
        if not self.id.strip():
            raise ValueError("DocumentationSection.id must not be blank")
        if not self.title_intent.strip():
            raise ValueError("DocumentationSection.title_intent must not be blank")
        for page in self.pages:
            if not page.strip():
                raise ValueError(
                    "DocumentationSection.pages must not contain a blank page id"
                )
        return self


class DocumentationRelation(BaseModel):
    """A cross-page relationship: ``from`` page -> ``to`` page of a ``type``.

    ``from`` is a Python keyword, so the field is ``from_`` backed by the authored
    ``from`` alias. All values are LLM-authored; Python only validates.
    """

    model_config = _PLAN_CONFIG

    from_: str = Field(default="", alias="from")
    to: str = ""
    type: str = ""

    @model_validator(mode="after")
    def _require_writable_relation(self) -> DocumentationRelation:
        """``from_`` / ``to`` must be non-blank page references.

        Pure structural check — Python does not judge whether the relationship is
        meaningful or whether the pages exist (page-existence consistency is a
        separate mechanical check against the PageSpec set).
        """
        if not self.from_.strip():
            raise ValueError("DocumentationRelation.from must not be blank")
        if not self.to.strip():
            raise ValueError("DocumentationRelation.to must not be blank")
        return self


class DocumentationPlan(BaseModel):
    """The Documentation Architect's page-structure plan.

    Expresses ``sections``, ``pages`` (page ids), ``relations``, and ``rationale``.
    Python only validates the schema and serializes; every page-split / grouping /
    ordering decision is the Architect's, never inferred by Python.

    Structural validation catches *pure* mistakes — a blank section id, a blank
    page id, duplicate section ids, duplicate page ids — which are always errors
    regardless of intent. It never judges which sections exist, which pages are
    needed, or whether the IA is sound.
    """

    model_config = _PLAN_CONFIG

    sections: list[DocumentationSection] = Field(default_factory=list)
    pages: list[str] = Field(default_factory=list)
    relations: list[DocumentationRelation] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _reject_duplicate_structure(self) -> DocumentationPlan:
        """Reject duplicate section ids and duplicate page ids.

        These are always structural errors: a section id or page id must uniquely
        identify one thing. Checks are scoped so the plan-level ``pages`` index
        may freely overlap a section's listing of the same page:

        * section ids are unique across the plan;
        * plan-level ``pages`` are unique among themselves (an index);
        * each section's ``pages`` are unique within that section;
        * a page referenced in two *different* sections is a duplicate reference.

        This is pure bookkeeping — Python never decides what a section/page
        should be.
        """
        section_ids: list[str] = [s.id for s in self.sections]
        if len(section_ids) != len(set(section_ids)):
            dupes = sorted({sid for sid in section_ids if section_ids.count(sid) > 1})
            raise ValueError(f"Duplicate DocumentationPlan section ids: {dupes}")

        if len(self.pages) != len(set(self.pages)):
            dupes = sorted({pid for pid in self.pages if self.pages.count(pid) > 1})
            raise ValueError(f"Duplicate DocumentationPlan page ids: {dupes}")

        for section in self.sections:
            pages = section.pages
            if len(pages) != len(set(pages)):
                dupes = sorted({pid for pid in pages if pages.count(pid) > 1})
                raise ValueError(
                    f"Duplicate page ids in DocumentationSection {section.id!r}: {dupes}"
                )

        section_page_sets: list[set[str]] = [set(s.pages) for s in self.sections]
        for i, pages in enumerate(section_page_sets):
            for other in section_page_sets[i + 1 :]:
                shared = sorted(pages & other)
                if shared:
                    raise ValueError(
                        "Duplicate DocumentationPlan page id referenced across "
                        f"sections: {shared}"
                    )
        return self


def plan_page_consistency_errors(
    plan: DocumentationPlan,
    page_specs: list[PageSpec],
) -> list[str]:
    """Return structural consistency errors between plan page refs and PageSpecs.

    This is a **mechanical cross-reference check**, not semantic planning. It
    reports only whether references *line up*:

    * duplicate ``PageSpec.page_id`` entries;
    * a page the plan lists (at plan level, in any section, or as a relation
      endpoint) for which no ``PageSpec`` exists.

    It deliberately NEVER judges whether a page should exist, whether the IA is
    sound, or which section a page belongs to — those are the Documentation
    Architect's decisions. Python reports discrepancies; the LLM decides intent.
    Returns an empty list when the plan and PageSpec set are structurally
    consistent.
    """
    errors: list[str] = []

    spec_ids: list[str] = [p.page_id for p in page_specs]
    if len(spec_ids) != len(set(spec_ids)):
        dupes = sorted({pid for pid in spec_ids if spec_ids.count(pid) > 1})
        errors.append(f"Duplicate PageSpec.page_id entries: {dupes}")

    spec_id_set: set[str] = set(spec_ids)

    planned: set[str] = set(plan.pages)
    for section in plan.sections:
        planned.update(section.pages)
    for rel in plan.relations:
        planned.add(rel.from_)
        planned.add(rel.to)

    for pid in sorted(planned):
        if pid not in spec_id_set:
            errors.append(
                f"DocumentationPlan references page {pid!r} with no matching PageSpec"
            )

    return errors
