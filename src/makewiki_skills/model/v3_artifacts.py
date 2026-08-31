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

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    @model_validator(mode="after")
    def _require_hypothesis_text(self) -> RepositoryHypothesis:
        """The hypothesis's key prose (``name`` / ``purpose``) must not be blank.

        An Orientation that produces no working hypothesis is not a usable
        RepositoryBrief. `type` / `confidence` keep their LLM-authored defaults;
        Python does not infer them.
        """
        if not self.name.strip() or not self.purpose.strip():
            raise ValueError(
                "RepositoryHypothesis.name and purpose must not be blank "
                "(a working hypothesis of what the project is)"
            )
        return self


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

    @model_validator(mode="after")
    def _require_path_and_reason(self) -> HighInformationSource:
        """A flagged high-information source must name its path and why."""
        if not self.path.strip() or not self.reason.strip():
            raise ValueError(
                "HighInformationSource.path and reason must not be blank"
            )
        return self


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

    @model_validator(mode="after")
    def _require_investigation_signal(self) -> RepositoryBrief:
        """A Brief must carry at least one investigation signal.

        ``major_areas`` may be absent, but then at least one ``important_unknown``
        must be recorded — otherwise the Brief is an empty shell that produces
        nothing to investigate.
        """
        if not self.major_areas and not self.important_unknowns:
            raise ValueError(
                "RepositoryBrief must have at least one major_area or one "
                "important_unknown"
            )
        return self


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

    @model_validator(mode="after")
    def _require_executable_contract(self) -> SubtaskSpec:
        """A SubtaskSpec must describe executable work, not an empty shell.

        ``id``, ``goal``, and ``expected_output.type`` / ``expected_output.id``
        must be non-blank and at least one ``stop_condition`` must be present so
        a subtask cannot run unbounded with no defined output. ``questions`` /
        ``scope_hint`` / ``depends_on`` may be empty. ``type`` is already
        constrained to the SubtaskType vocabulary. Python only checks structural
        completeness — it never judges whether the ``goal`` is semantically good
        nor schedules the subtask.
        """
        if not self.id.strip():
            raise ValueError("SubtaskSpec.id must not be blank")
        if not self.goal.strip():
            raise ValueError("SubtaskSpec.goal must not be blank")
        if not self.expected_output.type.strip() or not self.expected_output.id.strip():
            raise ValueError(
                "SubtaskSpec.expected_output.type and .id must not be blank"
            )
        if not self.stop_conditions:
            raise ValueError(
                "SubtaskSpec must declare at least one stop_condition"
            )
        return self


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

    @model_validator(mode="after")
    def _require_domain_text(self) -> InvestigationPlanDomain:
        """A domain must explain itself: ``id`` / ``why_important`` / ``goal`` non-blank.

        Python only checks structural completeness — it never judges whether a domain
        is actually important or its goal worthwhile. ``scope_hint`` /
        ``related_domains`` may stay empty (they are optional starting points /
        cross-links, not required prose).
        """
        if not self.id.strip():
            raise ValueError("InvestigationPlanDomain.id must not be blank")
        if not self.why_important.strip():
            raise ValueError(
                "InvestigationPlanDomain.why_important must not be blank"
            )
        if not self.goal.strip():
            raise ValueError("InvestigationPlanDomain.goal must not be blank")
        return self


class InvestigationPlan(BaseModel):
    """The handoff artifact produced by Orientation (see ``ARTIFACT_CONTRACTS`` §2).

    Lists the domains to investigate and the concrete investigation subtasks.
    Every field is LLM-authored; Python only validates the schema and serializes —
    it never schedules, orders, or decides which subtask is "ready".

    An InvestigationPlan must not be an empty shell: it carries a non-blank
    ``project_hypothesis``, and normally names at least one ``domain`` or one
    ``subtask``. If no investigation is warranted (``domains`` and ``subtasks`` are
    both empty), the plan must state an explicit ``no_investigation_reason`` —
    otherwise the plan would masquerade as a complete survey without explaining why
    nothing needs investigating. Python never judges whether an investigation is
    "good enough"; it only requires that the plan is not content-free and
    unexplained.
    """

    model_config = _ARTIFACT_CONFIG

    project_hypothesis: str = ""
    domains: list[InvestigationPlanDomain] = Field(default_factory=list)
    subtasks: list[SubtaskSpec] = Field(default_factory=list)
    coverage_questions: list[str] = Field(default_factory=list)
    known_uncertainties: list[str] = Field(default_factory=list)
    #: Required only when both ``domains`` and ``subtasks`` are empty: an explicit
    #: statement of why no further investigation is needed.
    no_investigation_reason: str | None = None

    @model_validator(mode="after")
    def _require_substantive_plan(self) -> InvestigationPlan:
        """A plan must be content-bearing: a non-blank hypothesis, and either
        investigation work (``domains`` / ``subtasks``) or an explicit reason why
        no investigation is warranted.

        Python only checks structural substance — it never judges whether the
        investigation is thorough or whether a domain/subtask is worthwhile.
        """
        if not self.project_hypothesis.strip():
            raise ValueError(
                "InvestigationPlan.project_hypothesis must not be blank"
            )
        if not self.domains and not self.subtasks:
            reason_blank = (
                not self.no_investigation_reason
                or not self.no_investigation_reason.strip()
            )
            if reason_blank:
                raise ValueError(
                    "InvestigationPlan with no domains and no subtasks must state "
                    "an explicit non-blank no_investigation_reason"
                )
        return self


class ClaimEvidence(BaseModel):
    """A provenance pointer backing a claim.

    ``path`` / ``symbol_or_location`` / ``rationale`` let a later reader verify
    the claim. Authored by the Explorer / Analyst LLM; Python only validates.
    """

    model_config = _ARTIFACT_CONFIG

    path: str = ""
    symbol_or_location: str = ""
    rationale: str = ""

    @model_validator(mode="after")
    def _require_path_and_rationale(self) -> ClaimEvidence:
        """A provenance pointer must name a path and explain why it supports."""
        if not self.path.strip() or not self.rationale.strip():
            raise ValueError("ClaimEvidence.path and rationale must not be blank")
        return self


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

    @model_validator(mode="after")
    def _require_grounded_claim(self) -> Claim:
        """A claim must be real text and at least minimally grounded.

        ``id`` / ``statement`` / ``semantic_key`` must be non-blank, and the
        claim must carry either at least one ``evidence`` item or an explicit
        ``uncertainty``. ``evidence=[]`` with ``uncertainty=None`` is forbidden:
        an ungrounded, un-hedged assertion would otherwise masquerade as valid
        canonical output. Python only checks this structural grounding — it never
        judges whether evidence actually supports the statement (that is an LLM /
        verification concern).
        """
        if not self.id.strip():
            raise ValueError("Claim.id must not be blank")
        if not self.statement.strip():
            raise ValueError("Claim.statement must not be blank")
        if not self.semantic_key.strip():
            raise ValueError("Claim.semantic_key must not be blank")
        uncertainty_blank = not self.uncertainty or not self.uncertainty.strip()
        if not self.evidence and uncertainty_blank:
            raise ValueError(
                "Claim must carry at least one evidence item or an explicit "
                "non-blank uncertainty"
            )
        return self


class ScopeExpansion(BaseModel):
    """A record of where an exploration stepped beyond its initial hint."""

    model_config = _ARTIFACT_CONFIG

    path: str = ""
    reason: str = ""

    @model_validator(mode="after")
    def _require_expansion_text(self) -> ScopeExpansion:
        """A scope expansion must name where it went (``path``) and why (``reason``).

        Pure structural check — Python never judges whether expanding into that
        path was warranted.
        """
        if not self.path.strip() or not self.reason.strip():
            raise ValueError("ScopeExpansion.path and reason must not be blank")
        return self


class ClaimBundle(BaseModel):
    """The artifact an investigation subtask produces (see ``ARTIFACT_CONTRACTS`` §3).

    One coherent semantic domain per bundle. Every claim carries evidence and an
    honest confidence; ``visibility`` / ``abstraction`` are LLM classifications,
    never Python inference. Python only validates the schema and serializes.

    A ClaimBundle must not be an empty shell: ``id`` / ``domain`` /
    ``producer_subtask`` / ``summary`` are non-blank, and it must carry at least one
    of ``claims`` / ``unresolved`` / ``recommended_followups`` /
    ``newly_discovered_areas``. An Explorer with no canonical claim must still say
    what it did not resolve, what it recommends next, or what new areas it found —
    an all-empty bundle would otherwise masquerade as completed investigation.
    Python never judges claim content correctness.
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

    @model_validator(mode="after")
    def _require_substantive_bundle(self) -> ClaimBundle:
        """A ClaimBundle must name its producer and surface and carry substance.

        ``id`` / ``domain`` / ``producer_subtask`` / ``summary`` must be non-blank,
        and at least one of ``claims`` / ``unresolved`` / ``recommended_followups`` /
        ``newly_discovered_areas`` must be present — an all-empty bundle would not
        be a completed investigation. Python only checks this structural substance;
        it never judges whether a claim is correct.
        """
        if not self.id.strip():
            raise ValueError("ClaimBundle.id must not be blank")
        if not self.domain.strip():
            raise ValueError("ClaimBundle.domain must not be blank")
        if not self.producer_subtask.strip():
            raise ValueError("ClaimBundle.producer_subtask must not be blank")
        if not self.summary.strip():
            raise ValueError("ClaimBundle.summary must not be blank")
        if not (
            self.claims
            or self.unresolved
            or self.recommended_followups
            or self.newly_discovered_areas
        ):
            raise ValueError(
                "ClaimBundle must carry at least one of claims / unresolved / "
                "recommended_followups / newly_discovered_areas"
            )
        return self


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

    @model_validator(mode="after")
    def _require_finding_text(self) -> ReviewFinding:
        """A finding must carry real text: ``id`` / ``severity`` / ``category`` /
        ``problem`` / ``required_change`` non-blank.

        ``location`` may be blank (not every finding pins to a line/path) and
        ``evidence_refs`` may be empty (a Reviewer may report a structural or
        documentation-design problem rather than a source-grounding one). Python
        only checks structural completeness — it never re-grades ``severity`` or
        judges whether the ``category`` is right.
        """
        for attr in ("id", "severity", "category", "problem", "required_change"):
            if not getattr(self, attr).strip():
                raise ValueError(
                    f"ReviewFinding.{attr} must not be blank"
                )
        return self


class ReviewFindings(BaseModel):
    """The read-only review output for one page / language (see ``ARTIFACT_CONTRACTS`` §8).

    The Reviewer emits findings but never modifies pages; a separate Revision
    Agent implements them and a fresh re-review decides completion. All judgment
    fields (``mode``, ``status``, per-finding ``severity``/``category``) are
    LLM-authored; Python only validates the schema and serializes.

    A ReviewFindings artifact must not be an empty shell: ``page_id`` /
    ``language`` / ``mode`` are non-blank, and ``status`` is one of ``passed`` /
    ``changes_required`` / ``blocked``. Each status must be backed by the matching
    evidence — ``passed`` needs at least one ``passed_check``, ``changes_required``
    needs at least one ``finding``, and ``blocked`` needs at least one
    ``unresolved`` — so a Reviewer cannot emit a bare verdict with nothing
    supporting it. Python never decides whether the Reviewer *should* pass or fail;
    it only checks the artifact is self-consistent.
    """

    model_config = _ARTIFACT_CONFIG

    page_id: str = ""
    language: str = ""
    mode: str = ""
    status: Literal["passed", "changes_required", "blocked"] = "changes_required"
    findings: list[ReviewFinding] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_self_consistent_status(self) -> ReviewFindings:
        """Each status must be backed by the matching evidence list.

        Python only checks that a Reviewer-authored verdict is self-consistent with
        the artifact's contents — it never decides whether the page should pass.
        """
        if not self.page_id.strip():
            raise ValueError("ReviewFindings.page_id must not be blank")
        if not self.language.strip():
            raise ValueError("ReviewFindings.language must not be blank")
        if not self.mode.strip():
            raise ValueError("ReviewFindings.mode must not be blank")
        if self.status == "passed":
            if not self.passed_checks:
                raise ValueError(
                    "status='passed' requires at least one passed_check"
                )
        elif self.status == "changes_required":
            if not self.findings:
                raise ValueError(
                    "status='changes_required' requires at least one finding"
                )
        elif self.status == "blocked":
            if not self.unresolved:
                raise ValueError(
                    "status='blocked' requires at least one unresolved item"
                )
        return self
