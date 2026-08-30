"""Model package for semantic analysis, claims, and ReBattle."""

from __future__ import annotations

from makewiki_skills.model.claim import (
    Claim,
    ClaimEvidence,
    ClaimSet,
    Confidence,
    MechanicalAssertion,
    VerificationState,
    VerificationStatus,
    build_claims_from_evidence,
    verify_claims_against_codebase,
)
from makewiki_skills.model.rebattle import (
    AdjudicatedClaim,
    AdjudicationResult,
    AgentClaim,
    AgentClaimBundle,
    AgentClaimSet,
)

__all__ = [
    "AdjudicatedClaim",
    "AdjudicationResult",
    "AgentClaim",
    "AgentClaimBundle",
    "AgentClaimSet",
    "Claim",
    "ClaimEvidence",
    "ClaimSet",
    "Confidence",
    "MechanicalAssertion",
    "VerificationState",
    "VerificationStatus",
    "build_claims_from_evidence",
    "verify_claims_against_codebase",
]
