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

from pydantic import BaseModel, ConfigDict, Field

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


class DocumentationRelation(BaseModel):
    """A cross-page relationship: ``from`` page -> ``to`` page of a ``type``.

    ``from`` is a Python keyword, so the field is ``from_`` backed by the authored
    ``from`` alias. All values are LLM-authored; Python only validates.
    """

    model_config = _PLAN_CONFIG

    from_: str = Field(default="", alias="from")
    to: str = ""
    type: str = ""


class DocumentationPlan(BaseModel):
    """The Documentation Architect's page-structure plan.

    Expresses ``sections``, ``pages`` (page ids), ``relations``, and ``rationale``.
    Python only validates the schema and serializes; every page-split / grouping /
    ordering decision is the Architect's, never inferred by Python.
    """

    model_config = _PLAN_CONFIG

    sections: list[DocumentationSection] = Field(default_factory=list)
    pages: list[str] = Field(default_factory=list)
    relations: list[DocumentationRelation] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
