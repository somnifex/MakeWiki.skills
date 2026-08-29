"""ReBattle competitive analysis models and cross-examination logic."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class AgentClaim(BaseModel):
    """A structured semantic assertion authored by an LLM scout/debate agent from a
    specific perspective.

    This is the *AgentClaim* layer of the four-layer claim vocabulary: a
    claim an LLM subagent authors about the project (commands, config keys,
    workflows, prerequisites, error cases). It is keyed by
    ``agent_id``/``perspective`` and is the input to ReBattle cross-examination.
    It is *not* a Python-mechanical fact and is *not* yet an accepted,
    adjudicated fact.
    """

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


# Deprecated: use AgentClaim. Kept as a module-level alias so existing
# ``from makewiki_skills.model.rebattle import Claim`` imports keep working.
Claim = AgentClaim


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
    claims: list[AgentClaim] = Field(default_factory=list)
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


class AdjudicatedClaim(BaseModel):
    """A consensus fact produced by the ReBattle + Judge pipeline.

    This is the *AdjudicatedClaim* layer of the four-layer claim vocabulary:
    an AgentClaim that has survived cross-examination and received an explicit
    ruling. One is produced per surviving claim when adjudications are supplied
    to :meth:`ReBattleArena.synthesize_consensus`.
    """

    claim: AgentClaim
    ruling: Literal["accepted", "rejected", "modified", "hedged"]
    final_assertion: str
    adjudicator_reasoning: str
    verified_via_codebase: bool = False


class AgentClaimSet(BaseModel):
    """A collection of claims extracted by a single agent."""

    agent_id: str
    perspective: str
    claims: list[AgentClaim] = Field(default_factory=list)


# Deprecated: use AgentClaimSet. Kept as a module-level alias so existing
# ``from makewiki_skills.model.rebattle import ClaimSet`` imports keep working.
ClaimSet = AgentClaimSet


class ReBattleResult(BaseModel):
    """Aggregate result of a ReBattle cross-examination session."""

    total_claims: int = 0
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    adjudications: list[AdjudicationResult] = Field(default_factory=list)
    consensus_facts: list[AgentClaim] = Field(default_factory=list)


class ReBattleArena:
    """Detects discrepancies between multiple AgentClaimSets and generates dispute matrices."""

    @staticmethod
    def detect_discrepancies(claim_sets: list[AgentClaimSet]) -> list[Discrepancy]:
        """Group claims by normalized key/topic and detect conflicts or contradictions."""
        claims_by_key: dict[tuple[str, str], list[AgentClaim]] = {}

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
        claim_sets: list[AgentClaimSet],
        adjudications: list[AdjudicationResult] | None = None,
    ) -> list[AgentClaim] | list[AdjudicatedClaim]:
        """Synthesize high-confidence consensus facts, filtering out rejected claims.

        When no adjudications are supplied, returns the surviving
        high-confidence ``AgentClaim`` facts (renamed value of the original
        behavior). When adjudications ARE supplied, returns one
        ``AdjudicatedClaim`` per surviving claim carrying its ruling — the
        accepted/rejected/modified/hedged disposition recorded by the Judge.
        """
        if not adjudications:
            return _consensus_agent_claims(claim_sets)

        # Adjudicated path: build a topic -> ruling lookup and produce one
        # AdjudicatedClaim per surviving (non-rejected) claim.
        ruling_by_topic: dict[str, AdjudicationResult] = {}
        for ruling in adjudications:
            ruling_by_topic[ruling.discrepancy_topic.lower()] = ruling

        seen: set[tuple[str, str]] = set()
        consensus: list[AdjudicatedClaim] = []

        for cset in claim_sets:
            for claim in cset.claims:
                topic = f"{claim.claim_type}:{(claim.value or claim.assertion).strip()}".lower()
                adj = ruling_by_topic.get(topic)

                # Any claim whose topic was explicitly rejected is dropped.
                if adj is not None and adj.ruling == "rejected":
                    continue

                key = (claim.claim_type, (claim.value or claim.assertion).strip().lower())
                if key in seen:
                    continue
                seen.add(key)

                if adj is not None:
                    consensus.append(
                        AdjudicatedClaim(
                            claim=claim,
                            ruling=adj.ruling,
                            final_assertion=adj.final_assertion,
                            adjudicator_reasoning=adj.adjudicator_reasoning,
                            verified_via_codebase=adj.verified_via_codebase,
                        )
                    )
                else:
                    # Surviving claim with no explicit dispute -> accepted as-is.
                    consensus.append(
                        AdjudicatedClaim(
                            claim=claim,
                            ruling="accepted",
                            final_assertion=claim.assertion,
                            adjudicator_reasoning="No dispute raised during cross-examination; claim accepted.",
                            verified_via_codebase=False,
                        )
                    )

        return consensus


def _consensus_agent_claims(
    claim_sets: list[AgentClaimSet],
    _adjudications: list[AdjudicationResult] | None = None,
) -> list[AgentClaim]:
    """(Legacy inner behavior) surviving high-confidence AgentClaims without rulings.

    Retains the pre-adjudication consensus shape for callers that do not
    supply adjudications. Rejected-topic filtering is a no-op here because
    without an adjudication list there are no rejected topics.
    """
    seen: set[tuple[str, str]] = set()
    consensus: list[AgentClaim] = []
    for cset in claim_sets:
        for claim in cset.claims:
            key = (claim.claim_type, (claim.value or claim.assertion).strip().lower())
            if key in seen:
                continue
            seen.add(key)
            consensus.append(claim)
    return consensus
