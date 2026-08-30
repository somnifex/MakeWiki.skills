"""Verification report models for L0-L5 layered verification architecture."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

# Verification honesty contract:
#   passed         - a verifier actually executed the check and proved it.
#   failed         - a verifier ran and found a contradiction.
#   pending        - no verifier ran / not yet proven (never "not verified -> passed").
#   unknown        - insufficient evidence to decide either way.
#   not_applicable - the level is genuinely irrelevant (emitted only there, e.g.
#                    cross-language parity for a single-language project).
# A check must never be marked "passed" unless it genuinely ran and proved the
# outcome.
VerificationStatus = Literal[
    "passed",
    "failed",
    "warning",
    "pending",
    "unknown",
    "not_applicable",
]

VerificationSource = Literal[
    "verified_from_repository",
    "generic_shell_semantics",
    "ast_declaration",
    "hedging_caveat",
    "markdown_linter",
    "cross_language_analyzer",
    "heuristic",
    "not_executed",
    "semantic_audit_bundle",
]

#: The confidence a semantic Auditor (LLM) attached to one verdict. Mirrors the
#: ``confidence`` field of :class:`~makewiki_skills.verification.semantic_audit.
#: SemanticAuditVerdict` so provenance never invents a new vocabulary.
SemanticConfidence = Literal["high", "medium", "low"]


class SemanticProvenance(BaseModel):
    """Structured provenance attached to a check merged from an LLM semantic
    audit bundle.

    This is the formal schema behind what was previously a loose
    ``dict[str, Any]``: each field is typed, so a downstream consumer (CLI
    report, eval scorer, Skill layer) reads real fields instead of parsing a
    free-form dictionary. It records *who judged, when, with what rationale and
    evidence, and how confidently* — it does NOT re-judge the verdict. It is
    ``None`` on a check that was not merged from a semantic audit bundle.
    """

    auditor: str
    rationale_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: SemanticConfidence = "medium"
    audited_at: str


class VerificationCheck(BaseModel):
    """A single verification check performed on a claim or document element."""

    check_id: str = Field(default_factory=lambda: f"chk-{uuid.uuid4().hex[:8]}")
    layer: str  # "L0", "L1", "L2", "L3", "L4", "L5"
    target: str  # document filename or claim_id
    language_code: str = "all"
    claim_type: str  # "command" | "path" | "config_key" | "structure" | "interface" | "behavior" | "epistemic"
    claim_text: str
    verified: bool
    status: VerificationStatus = "pending"
    verification_source: str = "verified_from_repository"
    detail: str
    suggested_fix: str | None = None
    #: Stable, deterministic semantic identity (e.g. ``L3:README.md:make build``,
    #: ``L4b:README:build``, ``L5:README.md:make build``) used to bind an LLM
    #: audit verdict to one specific check. It is deterministic and stable across
    #: re-runs when the underlying semantic item is unchanged — it is NEVER a
    #: random UUID (unlike ``check_id``).
    review_item_id: str | None = None
    #: Structured provenance from the LLM Auditor, populated by the item-level
    #: semantic-bundle merge (``verification_source == "semantic_audit_bundle"``).
    #: Holds the auditor, rationale, evidence refs, confidence and audited_at as
    #: a formal typed schema (``SemanticProvenance``) so downstream consumers
    #: (CLI report, eval scorer, Skill layer) can read them without parsing
    #: ``detail`` prose or a free-form dictionary. None when the check was not
    #: merged from an audit bundle.
    provenance: SemanticProvenance | None = None


class ReviewItem(BaseModel):
    """A registry entry of an expected semantic review item computed by Python.

    Computed after mechanical verification (before any bundle merge), this is the
    authoritative list of LLM-adjudicable review items for L3/L4b/L5. A bundle
    verdict may only adjudicate an item that exists here (matched by
    ``review_item_id``).
    """

    review_item_id: str
    layer: str  # "L3" | "L4b" | "L5"
    document: str  # filename / base name the item belongs to
    section: str  # section id or claim/section identity (may be "")
    evidence: list[str] = Field(default_factory=list)  # candidate evidence refs
    status: str = "pending"  # "pending" normally


class LayerReport(BaseModel):
    """Verification results for a single layer (e.g. L0 or L2)."""

    layer: str  # "L0", "L1", "L2", "L3", "L4", "L5"
    name: str  # e.g. "Syntax & Structure", "Interface"
    checks: list[VerificationCheck] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.verified)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.verified and c.status == "failed")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "warning")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> float:
        if not self.checks:
            return 1.0
        return round(self.passed_count / len(self.checks), 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> Literal["passed", "failed", "pending", "not_applicable"]:
        """Honest layer-level verdict derived from the individual checks.

        A layer is never ``passed`` merely because it has no failures: pending or
        unknown checks keep the verdict pending (LLM judgment), a layer whose
        checks are all genuinely not-applicable is ``not_applicable``, and a
        layer with no checks at all defaults to ``pending`` (nothing was proven).
        """
        checks = self.checks
        if not checks:
            return "pending"
        if any(c.status == "failed" for c in checks):
            return "failed"
        if any(c.status in ("pending", "unknown") for c in checks):
            return "pending"
        if all(c.status == "not_applicable" for c in checks):
            return "not_applicable"
        if self.passed_count > 0:
            return "passed"
        return "pending"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self.verdict == "passed"

    def failures(self) -> list[VerificationCheck]:
        """Checks that explicitly FAILED (``status == "failed"``).

        Pending and unknown checks are NOT failures: they have not proven a
        contradiction, they are simply unadjudicated.
        """
        return [c for c in self.checks if c.status == "failed"]

    def pending(self) -> list[VerificationCheck]:
        return [c for c in self.checks if c.status == "pending"]

    def unknowns(self) -> list[VerificationCheck]:
        return [c for c in self.checks if c.status == "unknown"]

    def warnings(self) -> list[VerificationCheck]:
        return [c for c in self.checks if c.status == "warning"]

    def not_applicable(self) -> list[VerificationCheck]:
        return [c for c in self.checks if c.status == "not_applicable"]


class ComprehensiveVerificationReport(BaseModel):
    """Aggregate multi-layer verification report covering L0 through L5."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    verified_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    layers: dict[str, LayerReport] = Field(default_factory=dict)
    #: Registry of expected semantic review items Python computes after
    #: mechanical verification. A bundle may only adjudicate items that exist
    #: here.
    review_items: list[ReviewItem] = Field(default_factory=list)
    #: Diagnostic / provenance metadata (e.g. a rejected bundle's unknown ids).
    details: dict[str, object] = Field(default_factory=dict)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_checks(self) -> int:
        return sum(layer.total_checks for layer in self.layers.values())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed_count(self) -> int:
        return sum(layer.passed_count for layer in self.layers.values())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_count(self) -> int:
        return sum(layer.failed_count for layer in self.layers.values())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> float:
        if self.total_checks == 0:
            return 1.0
        return round(self.passed_count / self.total_checks, 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verdict(self) -> Literal["passed", "failed", "pending", "not_applicable"]:
        """Aggregate verdict: failed if any layer failed; pending if any layer
        is pending; not_applicable if every layer is not_applicable; passed only
        if every layer is passed. A pending layer can never be overridden to a
        vacuous pass at the aggregate level."""
        layers = list(self.layers.values())
        if not layers:
            return "pending"
        if any(layer.verdict == "failed" for layer in layers):
            return "failed"
        if any(layer.verdict == "pending" for layer in layers):
            return "pending"
        if all(layer.verdict == "not_applicable" for layer in layers):
            return "not_applicable"
        if all(layer.verdict == "passed" for layer in layers):
            return "passed"
        return "pending"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self.verdict == "passed"


# ---------------------------------------------------------------------------
# Backward Compatibility Models
# ---------------------------------------------------------------------------


class GroundingClaim(BaseModel):
    """A specific verifiable claim found in a generated document."""

    claim_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    document: str
    language_code: str
    claim_text: str
    claim_type: str  # "command" | "config_key" | "path" | "version"


class GroundingViolation(BaseModel):
    """A claim that cannot be grounded in project evidence."""

    claim: GroundingClaim
    violation_type: str  # "ungrounded" | "contradicted" | "low_confidence"
    message: str
    suggested_fix: str | None = None


class GroundingReport(BaseModel):
    """Result of code-grounding verification across all documents."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    verified_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    total_claims: int = 0
    grounded_claims: int = 0
    violations: list[GroundingViolation] = Field(default_factory=list)
    warnings: list[GroundingViolation] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def grounding_score(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return round(self.grounded_claims / self.total_claims, 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return not any(v.violation_type == "contradicted" for v in self.violations)


class CodebaseCheck(BaseModel):
    """A single claim checked against the real project filesystem."""

    document: str
    language_code: str
    claim_text: str
    claim_type: Literal["path", "command", "config_key"]
    verified: bool
    detail: str
    verification_source: str = "verified_from_repository"


class CodebaseVerificationReport(BaseModel):
    """Result of verifying generated documents against the actual codebase."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    verified_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    checks: list[CodebaseCheck] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_checks(self) -> int:
        return len(self.checks)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.checks if c.verified)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.verified)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def score(self) -> float:
        if not self.checks:
            return 1.0
        return round(self.verified_count / len(self.checks), 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return self.failed_count == 0

    def failures(self) -> list[CodebaseCheck]:
        return [c for c in self.checks if not c.verified]
