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


def _claim(**kw):
    """Tiny factory so inline AgentClaim constructions default a semantic_key."""
    kw.setdefault("semantic_key", "unit.test.claim")
    return AgentClaim(**kw)


def test_canonical_names_exist() -> None:
    """AgentClaim / AgentClaimSet / AdjudicatedClaim are the canonical names."""
    assert AgentClaim.__name__ == "AgentClaim"
    assert AgentClaimSet.__name__ == "AgentClaimSet"
    assert AdjudicatedClaim.__name__ == "AdjudicatedClaim"


def test_deprecated_aliases_still_work() -> None:
    """Claim / ClaimSet are deprecated aliases for AgentClaim / AgentClaimSet."""
    assert DeprecatedClaim is AgentClaim
    assert DeprecatedClaimSet is AgentClaimSet


def test_agent_claim_requires_semantic_key() -> None:
    """semantic_key is the REQUIRED meaning used for cross-agent grouping."""
    with_sk = AgentClaim(
        agent_id="agent_red",
        semantic_key="network.port",
        assertion="Run app --port 8080",
    )
    assert with_sk.semantic_key == "network.port"
    # Omitting it is a validation error, not a silent optional.
    try:
        AgentClaim(agent_id="agent_red", assertion="Run app --port 8080")
    except Exception:
        return
    raise AssertionError("AgentClaim without semantic_key must fail validation")


def test_agent_claim_rejects_unknown_claim_type() -> None:
    """claim_type must be a member of the ClaimType vocabulary (no 'ngx')."""
    _claim(agent_id="agent_red", semantic_key="x.y", assertion="a", claim_type="command")
    try:
        _claim(agent_id="agent_red", semantic_key="x.y", assertion="a", claim_type="ngx")
    except Exception:
        return
    raise AssertionError("AgentClaim with claim_type 'ngx' must be rejected")


def test_agent_claim_evidence_refs_maps_from_source_file() -> None:
    """evidence_refs defaults and maps from source_file when present."""
    c = _claim(
        agent_id="agent_red",
        semantic_key="network.port",
        assertion="Run app --port 8080",
        source_file="src/app.py",
    )
    assert c.evidence_refs == ["src/app.py"]

    explicit = _claim(
        agent_id="agent_red",
        semantic_key="network.port",
        assertion="a",
        evidence_refs=["src/app.py", "src/config.py"],
    )
    assert explicit.evidence_refs == ["src/app.py", "src/config.py"]


def test_adjudicated_claim_model() -> None:
    claim = _claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        semantic_key="cli.command.run",
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
    """Different assertions, SAME semantic_key -> one discrepancy on meaning."""
    red_claim = _claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        semantic_key="cli.command.run",
        assertion="Run app --port 8080",
        value="app --port 8080",
        confidence="high",
    )
    blue_claim = _claim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="command",
        semantic_key="cli.command.run",
        assertion="Run app --port 3000 (default in config.py)",
        value="app --port 3000",
        confidence="medium",
    )

    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[red_claim])
    set_blue = AgentClaimSet(
        agent_id="agent_blue", perspective="code_implementation", claims=[blue_claim]
    )

    discrepancies = ReBattleArena.detect_discrepancies([set_red, set_blue])
    assert len(discrepancies) == 1
    assert discrepancies[0].claim_type == "command"
    assert discrepancies[0].topic == "cli.command.run"
    assert len(discrepancies[0].claims) == 2


def test_rebattle_groups_by_semantic_key() -> None:
    """Grouping keys on MEANING (semantic_key), never on value.

    * Different values + same semantic_key -> ONE discrepancy.
    * Same value + different semantic_key -> NO collision (two, unrelated claims).
    """
    a = _claim(agent_id="agent_red", semantic_key="network.port", assertion="port 8080", value="8080")
    b = _claim(agent_id="agent_blue", semantic_key="network.port", assertion="port 3000", value="3000")
    c = _claim(agent_id="agent_green", semantic_key="db.port", assertion="port 8080", value="8080")

    sets = [
        AgentClaimSet(agent_id="agent_red", perspective="u", claims=[a]),
        AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[b]),
        AgentClaimSet(agent_id="agent_green", perspective="d", claims=[c]),
    ]

    discs = ReBattleArena.detect_discrepancies(sets)
    # network.port: a + b (2 distinct agents, 2 assertions) -> discrepancy.
    # db.port: c alone -> single-agent, no conflict, no low/inferred -> NOT a discrepancy.
    keys = {d.topic for d in discs}
    assert keys == {"network.port"}
    port_disc = next(d for d in discs if d.topic == "network.port")
    assert {cl.agent_id for cl in port_disc.claims} == {"agent_red", "agent_blue"}


def test_get_claims_do_not_collide_across_semantic_keys() -> None:
    """Same assertion under different semantic_keys is NOT a conflict."""
    a = _claim(agent_id="agent_red", semantic_key="cli.command.run", assertion="app --port 8080")
    b = _claim(
        agent_id="agent_blue", semantic_key="config.parameter.port", assertion="app --port 8080"
    )
    sets = [
        AgentClaimSet(agent_id="agent_red", perspective="u", claims=[a]),
        AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[b]),
    ]
    discs = ReBattleArena.detect_discrepancies(sets)
    assert discs == []


def test_synthesize_consensus_filters_rejected() -> None:
    claim1 = _claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        semantic_key="cli.command.fast",
        assertion="app --fast",
        value="app --fast",
        confidence="inferred",
    )
    claim2 = _claim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="command",
        semantic_key="cli.command.help",
        assertion="app --help",
        value="app --help",
        confidence="high",
    )

    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[claim1])
    set_blue = AgentClaimSet(agent_id="agent_blue", perspective="code_implementation", claims=[claim2])

    adjudications = [
        AdjudicationResult(
            discrepancy_topic="cli.command.fast",
            ruling="rejected",
            final_assertion="Flag --fast is invalid",
            adjudicator_reasoning="Verified via parser AST that flag does not exist",
        )
    ]

    consensus = ReBattleArena.synthesize_consensus([set_red, set_blue], adjudications)
    # The rejected claim's semantic_key is dropped.
    assert len(consensus) == 1
    # The surviving dispute-free claim stays a PENDING AgentClaim — no auto-accept.
    assert isinstance(consensus[0], AgentClaim)
    assert not isinstance(consensus[0], AdjudicatedClaim)
    assert consensus[0].semantic_key == "cli.command.help"


def test_rebattle_does_not_auto_accept_undisputed_claim() -> None:
    """A claim with an explicit AdjudicationResult becomes an AdjudicatedClaim;
    an undisputed (no-ruling) claim is left as a pending AgentClaim — never
    fabricated 'accepted'."""
    undisputed = _claim(
        agent_id="agent_red",
        semantic_key="cli.command.help",
        assertion="app --help",
    )
    adjudicated = _claim(
        agent_id="agent_blue",
        semantic_key="cli.command.port",
        assertion="app --port 8080",
    )
    sets = [
        AgentClaimSet(agent_id="agent_red", perspective="u", claims=[undisputed]),
        AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[adjudicated]),
    ]
    adjudications = [
        AdjudicationResult(
            discrepancy_topic="cli.command.port",
            ruling="accepted",
            final_assertion="app --port 8080",
            adjudicator_reasoning="Verified against config",
        )
    ]

    consensus = ReBattleArena.synthesize_consensus(sets, adjudications)
    by_key = {
        (c.claim.semantic_key if isinstance(c, AdjudicatedClaim) else c.semantic_key): c
        for c in consensus
    }

    # The explicitly adjudicated claim is wrapped with the Judge's ruling.
    assert isinstance(by_key["cli.command.port"], AdjudicatedClaim)
    assert by_key["cli.command.port"].ruling == "accepted"

    # The undisputed claim is NOT wrapped and has NO fabricated ruling.
    pending = by_key["cli.command.help"]
    assert isinstance(pending, AgentClaim)
    assert not isinstance(pending, AdjudicatedClaim)


def test_synthesize_consensus_without_adjudications_returns_agent_claims() -> None:
    """Without adjudications, consensus retains the surviving AgentClaims."""
    claim1 = _claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        semantic_key="cli.command.port",
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
    claim = _claim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="command",
        semantic_key="cli.command.fast",
        assertion="app --fast",
        value="app --fast",
        confidence="medium",
    )
    set_red = AgentClaimSet(agent_id="agent_red", perspective="user_experience", claims=[claim])

    adjudications = [
        AdjudicationResult(
            discrepancy_topic="cli.command.fast",
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
