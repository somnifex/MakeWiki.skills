"""Unit tests for ReBattle models and arena logic (AgentClaim vocabulary)."""

from __future__ import annotations

from makewiki_skills.model.rebattle import (
    AdjudicatedClaim,
    AdjudicationResult,
    AgentClaim,
    AgentClaimSet,
    ReBattleArena,
)
from makewiki_skills.model.rebattle import Claim as DeprecatedClaim
from makewiki_skills.model.rebattle import ClaimSet as DeprecatedClaimSet


def test_canonical_names_exist() -> None:
    """AgentClaim / AgentClaimSet / AdjudicatedClaim are the canonical names."""
    assert AgentClaim.__name__ == "AgentClaim"
    assert AgentClaimSet.__name__ == "AgentClaimSet"
    assert AdjudicatedClaim.__name__ == "AdjudicatedClaim"


def test_deprecated_aliases_still_work() -> None:
    """Claim / ClaimSet are deprecated aliases for AgentClaim / AgentClaimSet."""
    assert DeprecatedClaim is AgentClaim
    assert DeprecatedClaimSet is AgentClaimSet


def test_adjudicated_claim_model() -> None:
    claim = AgentClaim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="Run app --port 8080",
        value="app --port 8080",
        confidence="high",
    )
    adj = AdjudicatedClaim(
        claim=claim,
        ruling="accepted",
        final_assertion="Run app --port 8080",
        adjudicator_reasoning="Verified against parser AST",
        verified_via_codebase=True,
    )
    assert adj.ruling == "accepted"
    assert adj.verified_via_codebase is True
    assert adj.claim is claim


def test_detect_discrepancies_finds_conflicts() -> None:
    red_claim = AgentClaim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="Run app --port 8080",
        value="app --port 8080",
        confidence="high",
    )
    blue_claim = AgentClaim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="command",
        assertion="Run app --port 3000 (default in config.py)",
        value="app --port 8080",
        confidence="medium",
    )

    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[red_claim])
    set_blue = AgentClaimSet(
        agent_id="agent_blue", perspective="code_implementation", claims=[blue_claim]
    )

    discrepancies = ReBattleArena.detect_discrepancies([set_red, set_blue])
    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "command"
    assert len(discrepancies[0].claims) == 2


def test_synthesize_consensus_filters_rejected() -> None:
    claim1 = AgentClaim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="app --fast",
        value="app --fast",
        confidence="inferred",
    )
    claim2 = AgentClaim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="command",
        assertion="app --help",
        value="app --help",
        confidence="high",
    )

    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[claim1])
    set_blue = AgentClaimSet(agent_id="agent_blue", perspective="code_implementation", claims=[claim2])

    adjudications = [
        AdjudicationResult(
            discrepancy_topic="command:app --fast",
            ruling="rejected",
            final_assertion="Flag --fast is invalid",
            adjudicator_reasoning="Verified via parser AST that flag does not exist",
        )
    ]

    consensus = ReBattleArena.synthesize_consensus([set_red, set_blue], adjudications)
    assert isinstance(consensus[0], AdjudicatedClaim)
    assert len(consensus) == 1
    assert consensus[0].claim.value == "app --help"
    # The surviving undisputed claim is adjudicated as "accepted".
    assert consensus[0].ruling == "accepted"


def test_synthesize_consensus_without_adjudications_returns_agent_claims() -> None:
    """Without adjudications, consensus retains the surviving AgentClaims."""
    claim1 = AgentClaim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="app --port 8080",
        value="app --port 8080",
        confidence="high",
    )
    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[claim1])

    consensus = ReBattleArena.synthesize_consensus([set_red])
    assert len(consensus) == 1
    assert isinstance(consensus[0], AgentClaim)
    assert not isinstance(consensus[0], AdjudicatedClaim)
    assert consensus[0].value == "app --port 8080"


def test_synthesize_consensus_modified_ruling() -> None:
    claim = AgentClaim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="app --fast",
        value="app --fast",
        confidence="medium",
    )
    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[claim])

    adjudications = [
        AdjudicationResult(
            discrepancy_topic="command:app --fast",
            ruling="modified",
            final_assertion="app --fast (requires --no-cache)",
            adjudicator_reasoning="Flag exists but requires an additional flag",
            verified_via_codebase=True,
        )
    ]

    consensus = ReBattleArena.synthesize_consensus([set_red], adjudications)
    assert len(consensus) == 1
    assert consensus[0].ruling == "modified"
    assert consensus[0].final_assertion == "app --fast (requires --no-cache)"
    assert consensus[0].verified_via_codebase is True
