"""Verification report models for L0-L5 layered verification architecture."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from makewiki_skills.generator.language_generator import GeneratedDocument

VerificationStatus = Literal["passed", "failed", "warning", "pending", "not_applicable"]

VerificationSource = Literal[
    "verified_from_repository",
    "generic_shell_semantics",
    "ast_declaration",
    "hedging_caveat",
    "markdown_linter",
    "cross_language_analyzer",
    "heuristic",
]


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
    def passed(self) -> bool:
        return self.failed_count == 0

    def failures(self) -> list[VerificationCheck]:
        return [c for c in self.checks if not c.verified]


class ComprehensiveVerificationReport(BaseModel):
    """Aggregate multi-layer verification report covering L0 through L5."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    verified_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    layers: dict[str, LayerReport] = Field(default_factory=dict)

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
    def passed(self) -> bool:
        return all(layer.passed for layer in self.layers.values())


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
