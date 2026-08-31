"""LLM-authored PageSpec validation model.

A PageSpec is the Writer's contract: it binds a Writer to a single page, its
``required_sections``, ``covers``, and forbidden topics — so a Writer never
"understands the repository and decides what to document". Every field is
**authored by the Documentation Architect LLM**; Python only validates the schema
and serializes.

Python MUST NOT split pages automatically, infer a page type, or decide what gets
documented. The only mechanical check here is that ``page_type`` is one of the
allowed vocabulary values (``references/v3/PAGE_SPEC.md`` §3). See that file for
the core contract (§2) and per-type requirements (§4).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Forbid unknown keys so a hand-authored PageSpec with a typo'd or unexpected
#: key fails loudly at load time instead of being silently dropped.
_SPEC_CONFIG = ConfigDict(extra="forbid")

#: Allowed page types (``PAGE_SPEC`` §3). Validation only — Python never chooses
#: a page type, and not every project uses all of these.
PageType = Literal[
    "landing",
    "tutorial",
    "how_to",
    "feature_guide",
    "concept",
    "reference",
    "api_reference",
    "troubleshooting",
    "runbook",
]


class PageSpec(BaseModel):
    """The Writer's contract for one page (``PAGE_SPEC`` §2).

    All fields are LLM-authored; Python only validates the schema, checks that
    ``page_type`` is in the allowed vocabulary, and serializes. It never splits
    pages, infers page type, or decides what gets documented.
    """

    model_config = _SPEC_CONFIG

    page_id: str = ""
    page_type: PageType = "concept"
    title_intent: str = ""
    audience: list[str] = Field(default_factory=list)
    user_goal: str = ""
    covers: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    required_facts: list[str] = Field(default_factory=list)
    optional_facts: list[str] = Field(default_factory=list)
    forbidden_topics: list[str] = Field(default_factory=list)
    source_claims: list[str] = Field(default_factory=list)
    semantic_refs: list[str] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
    related_pages: list[str] = Field(default_factory=list)
    language: str = ""
