"""Unit tests for ReBattle models and arena logic."""

from __future__ import annotations

from makewiki_skills.model.rebattle import (
    AdjudicationResult,
    Claim,
    ClaimSet,
    ReBattleArena,
)


def test_detect_discrepancies_finds_conflicts() -> None:
    red_claim = Claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="Run app --port 8080",
        value="app --port 8080",
        confidence="high",
    )
    blue_claim = Claim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="command",
        assertion="Run app --port 3000 (default in config.py)",
        value="app --port 8080",
        confidence="medium",
    )

    set_red = ClaimSet(agent_id="agent_red", perspective="user_experience", claims=[red_claim])
    set_blue = ClaimSet(
        agent_id="agent_blue", perspective="code_implementation", claims=[blue_claim]
    )

    discrepancies = ReBattleArena.detect_discrepancies([set_red, set_blue])
    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "command"
    assert len(discrepancies[0].claims) == 2


def test_synthesize_consensus_filters_rejected() -> None:
    claim1 = Claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        assertion="app --fast",
        value="app --fast",
        confidence="inferred",
    )
    claim2 = Claim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="command",
        assertion="app --help",
        value="app --help",
        confidence="high",
    )

    set_red = ClaimSet(agent_id="agent_red", perspective="user_experience", claims=[claim1])
    set_blue = ClaimSet(agent_id="agent_blue", perspective="code_implementation", claims=[claim2])

    adjudications = [
        AdjudicationResult(
            discrepancy_topic="command:app --fast",
            ruling="rejected",
            final_assertion="Flag --fast is invalid",
            adjudicator_reasoning="Verified via parser AST that flag does not exist",
        )
    ]

    consensus = ReBattleArena.synthesize_consensus([set_red, set_blue], adjudications)
    assert len(consensus) == 1
    assert consensus[0].value == "app --help"
