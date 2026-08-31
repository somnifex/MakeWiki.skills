"""V3 cognitive handoff artifacts.

These models describe the handoff contracts between cognitive phases (see
``references/v3/ARTIFACT_CONTRACTS.md``). They are **LLM-authored** artifacts:
every field is produced by the Orientation / Analysis / Authoring LLM, and Python
only performs **schema validation and serialization**. Python MUST NOT infer,
classify, or invent any field's semantic content from filenames, keywords, or
patterns.

Phase C implements these validation models incrementally. This module currently
holds the ``RepositoryBrief`` model only; later phases add ``InvestigationPlan``,
``SubtaskSpec``, ``ClaimBundle``, and ``ReviewFindings`` models in the same file.

All models use ``extra="forbid"`` so a hand-authored artifact with a typo'd or
unexpected key fails loudly at load time instead of being silently dropped,
mirroring the strictness of other hand-authored plans
(see :mod:`makewiki_skills.model.site_presentation`).

Fields that the source / LLM cannot establish are simply omitted or left
``None``/empty — never guessed by Python.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Forbid unknown keys so a hand-authored artifact with a typo'd or unexpected
#: key fails loudly at validation time instead of being silently dropped.
_ARTIFACT_CONFIG = ConfigDict(extra="forbid")


class RepositoryHypothesis(BaseModel):
    """The Orientation LLM's working hypothesis of what the project is.

    Python only validates and serializes; it never derives ``purpose`` or
    ``type`` from filenames or structure.
    """

    model_config = _ARTIFACT_CONFIG

    name: str = ""
    purpose: str = ""
    type: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"


class LikelyUser(BaseModel):
    """A candidate audience the Orientation LLM hypothesizes."""

    model_config = _ARTIFACT_CONFIG

    persona_hint: str = ""
    reason: str = ""


class MajorArea(BaseModel):
    """A coherent area the Orientation LLM identifies as worth investigating."""

    model_config = _ARTIFACT_CONFIG

    id: str = ""
    meaning_hypothesis: str = ""
    likely_paths: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"


class HighInformationSource(BaseModel):
    """A source path the Orientation LLM flags as highly informative."""

    model_config = _ARTIFACT_CONFIG

    path: str = ""
    reason: str = ""


class ExistingDocumentation(BaseModel):
    """A pre-existing documentation location and its judged standing."""

    model_config = _ARTIFACT_CONFIG

    path_or_url: str = ""
    standing: Literal["current", "possibly_stale", "unknown"] = "unknown"


class RepositoryBrief(BaseModel):
    """The handoff artifact produced by Orientation.

    Captures the Orientation LLM's working understanding so downstream agents do
    not each re-derive the repository from scratch. Every field is LLM-authored;
    Python only validates the schema and serializes it.
    """

    model_config = _ARTIFACT_CONFIG

    project_hypothesis: RepositoryHypothesis = Field(
        default_factory=RepositoryHypothesis
    )
    likely_users: list[LikelyUser] = Field(default_factory=list)
    major_areas: list[MajorArea] = Field(default_factory=list)
    high_information_sources: list[HighInformationSource] = Field(
        default_factory=list
    )
    existing_documentation: list[ExistingDocumentation] = Field(
        default_factory=list
    )
    important_unknowns: list[str] = Field(default_factory=list)
    orientation_notes: list[str] = Field(default_factory=list)
