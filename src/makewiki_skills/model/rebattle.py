"""ReBattle competitive analysis models and cross-examination logic."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class Claim(BaseModel):
    """A structured assertion made by an agent from a specific perspective."""

    claim_id: str = Field(default_factory=lambda: f"claim-{uuid.uuid4().hex[:8]}")
    agent_id: str  # e.g. "agent_red", "agent_blue", "agent_green"
    perspective: str = (
        "user_experience"  # "user_experience" | "code_implementation" | "deployment_ops"
    )
    claim_type: str = (
        "command"  # "command" | "config_key" | "path" | "workflow" | "error_case" | "prerequisite"
    )
    assertion: str
    value: str | None = None
    source_file: str | None = None
    line_range: tuple[int, int] | None = None
    raw_evidence: str | None = None
    confidence: Literal["high", "medium", "low", "inferred"] = "medium"


class Challenge(BaseModel):
    """An objection or question raised against a claim during cross-examination."""

    challenge_id: str = Field(default_factory=lambda: f"chg-{uuid.uuid4().hex[:8]}")
    target_claim_id: str
    challenger_agent_id: str
    objection_type: Literal[
        "nonexistent_feature",
        "incorrect_default",
        "missing_prerequisite",
        "unreleased_code",
        "inaccurate_description",
    ] = "inaccurate_description"
    argument: str
    counter_evidence: str | None = None
    severity: Literal["critical", "major", "minor"] = "major"


class Discrepancy(BaseModel):
    """A detected divergence or debate point between different agent perspectives."""

    topic: str
    claim_type: str
    claims: list[Claim] = Field(default_factory=list)
    challenges: list[Challenge] = Field(default_factory=list)
    status: Literal["open", "resolved", "dismissed"] = "open"


class AdjudicationResult(BaseModel):
    """The final ruling made by the Judge / Orchestrator on a disputed fact."""

    discrepancy_topic: str
    ruling: Literal["accepted", "rejected", "modified", "hedged"]
    final_assertion: str
    adjudicator_reasoning: str
    verified_via_codebase: bool = False
    source_claim_id: str | None = None


class ClaimSet(BaseModel):
    """A collection of claims extracted by a single agent."""

    agent_id: str
    perspective: str
    claims: list[Claim] = Field(default_factory=list)


class ReBattleResult(BaseModel):
    """Aggregate result of a ReBattle cross-examination session."""

    total_claims: int = 0
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    adjudications: list[AdjudicationResult] = Field(default_factory=list)
    consensus_facts: list[Claim] = Field(default_factory=list)


class ReBattleArena:
    """Detects discrepancies between multiple ClaimSets and generates dispute matrices."""

    @staticmethod
    def detect_discrepancies(claim_sets: list[ClaimSet]) -> list[Discrepancy]:
        """Group claims by normalized key/topic and detect conflicts or contradictions."""
        claims_by_key: dict[tuple[str, str], list[Claim]] = {}

        for cset in claim_sets:
            for claim in cset.claims:
                key_token = (claim.value or claim.assertion).strip().lower()
                key = (claim.claim_type, key_token)
                claims_by_key.setdefault(key, []).append(claim)

        discrepancies: list[Discrepancy] = []

        for (ctype, val), matched_claims in claims_by_key.items():
            confidences = {c.confidence for c in matched_claims}
            agents = {c.agent_id for c in matched_claims}

            if len(matched_claims) > 1 and len(agents) > 1:
                assertions = {c.assertion.strip() for c in matched_claims}
                if len(assertions) > 1 or "inferred" in confidences:
                    discrepancies.append(
                        Discrepancy(
                            topic=f"{ctype}:{val}",
                            claim_type=ctype,
                            claims=matched_claims,
                            status="open",
                        )
                    )
            elif "inferred" in confidences or "low" in confidences:
                discrepancies.append(
                    Discrepancy(
                        topic=f"{ctype}:{val}",
                        claim_type=ctype,
                        claims=matched_claims,
                        status="open",
                    )
                )

        return discrepancies

    @staticmethod
    def synthesize_consensus(
        claim_sets: list[ClaimSet],
        adjudications: list[AdjudicationResult] | None = None,
    ) -> list[Claim]:
        """Synthesize high-confidence consensus facts, filtering out rejected claims."""
        rejected_topics = set()
        modified_map: dict[str, str] = {}

        if adjudications:
            for adj in adjudications:
                if adj.ruling == "rejected":
                    rejected_topics.add(adj.discrepancy_topic.lower())
                elif adj.ruling in ("modified", "hedged"):
                    modified_map[adj.discrepancy_topic.lower()] = adj.final_assertion

        seen: set[tuple[str, str]] = set()
        consensus: list[Claim] = []

        for cset in claim_sets:
            for claim in cset.claims:
                topic = f"{claim.claim_type}:{(claim.value or claim.assertion).strip()}".lower()
                if topic in rejected_topics:
                    continue

                key = (claim.claim_type, (claim.value or claim.assertion).strip().lower())
                if key in seen:
                    continue

                seen.add(key)
                if topic in modified_map:
                    claim_copy = claim.model_copy(deep=True)
                    claim_copy.assertion = modified_map[topic]
                    consensus.append(claim_copy)
                else:
                    consensus.append(claim)

        return consensus
