"""V3 cognitive handoff artifacts.

These models describe the handoff contracts between cognitive phases (see
``references/v3/ARTIFACT_CONTRACTS.md``). They are **LLM-authored** artifacts:
every field is produced by the Orientation / Analysis / Authoring LLM, and Python
only performs **schema validation and serialization**. Python MUST NOT infer,
classify, or invent any field's semantic content from filenames, keywords, or
patterns.

Phase C implements these validation models incrementally. This module currently
holds the ``RepositoryBrief``, ``SubtaskSpec``, ``InvestigationPlan``,
``ClaimBundle``, and ``ReviewFindings`` models.

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


#: Allowed subtask types. Validated only — Python never selects or schedules
#: subtasks nor decides which is "ready".
SubtaskType = Literal[
    "orientation",
    "investigation",
    "semantic_synthesis",
    "conflict_resolution",
    "documentation_modeling",
    "page_planning",
    "writing",
    "review",
    "revision",
    "integration",
]


class SubtaskOutputSpec(BaseModel):
    """The expected artifact a subtask produces (type + stable id).

    The expected/target artifact type and id are authored by the orchestrating
    LLM. Python only validates; it does not resolve or enforce the artifact.
    """

    model_config = _ARTIFACT_CONFIG

    type: str = ""
    id: str = ""


class SubtaskSpec(BaseModel):
    """The basic V3 orchestration contract (see ``references/v3/SUBTASK_PROTOCOL.md``).

    A SubtaskSpec is authored by the orchestrating LLM so that different Coding
    Agents / Harnesses can understand it directly — Python is **not** a scheduler
    and does not select, ready, or run subtasks. Python only validates the schema.
    ``scope_hint`` is a recommended starting point, never a hard file allowlist.
    """

    model_config = _ARTIFACT_CONFIG

    id: str = ""
    type: SubtaskType = "investigation"
    goal: str = ""
    context: str = ""
    scope_hint: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    expected_output: SubtaskOutputSpec = Field(default_factory=SubtaskOutputSpec)
    depends_on: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)


class InvestigationPlanDomain(BaseModel):
    """One coherent semantic domain the InvestigationPlan targets.

    Authored by the Orientation / planning LLM. ``scope_hint`` lists recommended
    starting points only — it is not a hard file allowlist (``SUBTASK_PROTOCOL``).
    """

    model_config = _ARTIFACT_CONFIG

    id: str = ""
    why_important: str = ""
    goal: str = ""
    scope_hint: list[str] = Field(default_factory=list)
    related_domains: list[str] = Field(default_factory=list)


class InvestigationPlan(BaseModel):
    """The handoff artifact produced by Orientation (see ``ARTIFACT_CONTRACTS`` §2).

    Lists the domains to investigate and the concrete investigation subtasks.
    Every field is LLM-authored; Python only validates the schema and serializes —
    it never schedules, orders, or decides which subtask is "ready".
    """

    model_config = _ARTIFACT_CONFIG

    project_hypothesis: str = ""
    domains: list[InvestigationPlanDomain] = Field(default_factory=list)
    subtasks: list[SubtaskSpec] = Field(default_factory=list)
    coverage_questions: list[str] = Field(default_factory=list)
    known_uncertainties: list[str] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    """A provenance pointer backing a claim.

    ``path`` / ``symbol_or_location`` / ``rationale`` let a later reader verify
    the claim. Authored by the Explorer / Analyst LLM; Python only validates.
    """

    model_config = _ARTIFACT_CONFIG

    path: str = ""
    symbol_or_location: str = ""
    rationale: str = ""


class Claim(BaseModel):
    """A single, evidence-backed assertion about stable behavior or an interface.

    ``visibility`` and ``abstraction`` are **LLM classifications** (see
    ``ARTIFACT_CONTRACTS`` §3). Python must never infer them from directory
    names, AST patterns, or framework conventions — it treats them as opaque
    strings written by the Analyst / Explorer and does not classify.
    """

    model_config = _ARTIFACT_CONFIG

    id: str = ""
    statement: str = ""
    semantic_key: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"
    visibility: list[str] = Field(default_factory=list)
    abstraction: str = ""
    evidence: list[ClaimEvidence] = Field(default_factory=list)
    uncertainty: str | None = None


class ScopeExpansion(BaseModel):
    """A record of where an exploration stepped beyond its initial hint."""

    model_config = _ARTIFACT_CONFIG

    path: str = ""
    reason: str = ""


class ClaimBundle(BaseModel):
    """The artifact an investigation subtask produces (see ``ARTIFACT_CONTRACTS`` §3).

    One coherent semantic domain per bundle. Every claim carries evidence and an
    honest confidence; ``visibility`` / ``abstraction`` are LLM classifications,
    never Python inference. Python only validates the schema and serializes.
    """

    model_config = _ARTIFACT_CONFIG

    id: str = ""
    domain: str = ""
    producer_subtask: str = ""
    summary: str = ""
    claims: list[Claim] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    newly_discovered_areas: list[str] = Field(default_factory=list)
    recommended_followups: list[str] = Field(default_factory=list)
    scope_expansions: list[ScopeExpansion] = Field(default_factory=list)


class ReviewFinding(BaseModel):
    """A single finding produced by a read-only Reviewer.

    ``severity`` / ``category`` are LLM-authored judgment strings (Python does
    not classify or re-grade them). ``evidence_refs`` point at what supports or
    contradicts the finding. Python only validates the schema; the Reviewer does
    not edit pages (see ``tasks/review.md``, ``tasks/revise.md``).
    """

    model_config = _ARTIFACT_CONFIG

    id: str = ""
    severity: str = ""
    category: str = ""
    location: str = ""
    problem: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    required_change: str = ""


class ReviewFindings(BaseModel):
    """The read-only review output for one page / language (see ``ARTIFACT_CONTRACTS`` §8).

    The Reviewer emits findings but never modifies pages; a separate Revision
    Agent implements them and a fresh re-review decides completion. All judgment
    fields (``mode``, ``status``, per-finding ``severity``/``category``) are
    LLM-authored; Python only validates the schema and serializes.
    """

    model_config = _ARTIFACT_CONFIG

    page_id: str = ""
    language: str = ""
    mode: str = ""
    status: str = ""
    findings: list[ReviewFinding] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
