"""Unit tests for ReBattle models and arena logic (AgentClaim vocabulary)."""

from __future__ import annotations

import pytest

from makewiki_skills.model.rebattle import (
    AdjudicatedClaim,
    AdjudicationResult,
    AgentClaim,
    AgentClaimBundle,
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
    """claim_type is a strict ClaimType Literal — 'ngx' is rejected at ingress."""
    _claim(agent_id="agent_red", semantic_key="x.y", assertion="a", claim_type="command")
    with pytest.raises(ValueError):
        _claim(agent_id="agent_red", semantic_key="x.y", assertion="a", claim_type="ngx")


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


def test_identical_prose_different_structured_value_flagged() -> None:
    """Same semantic_key + IDENTICAL assertion prose, but different structured
    value (3000 vs 8080) -> a hard structured_conflict.

    This is the case the old assertion-set-difference logic MISSED: matching
    prose must never hide a real value conflict.
    """
    red = _claim(
        agent_id="agent_red",
        semantic_key="network.port",
        assertion="The app listens on the configured port.",
        value="3000",
    )
    blue = _claim(
        agent_id="agent_blue",
        semantic_key="network.port",
        assertion="The app listens on the configured port.",
        value="8080",
    )
    discs = ReBattleArena.detect_discrepancies(
        [
            AgentClaimSet(agent_id="agent_red", perspective="u", claims=[red]),
            AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[blue]),
        ]
    )
    assert len(discs) == 1
    assert discs[0].topic == "network.port"
    assert discs[0].kind == "structured_conflict"
    assert discs[0].status == "open"


def test_identical_prose_different_payload_flagged() -> None:
    """Same semantic_key + IDENTICAL prose, differing structured payload dicts
    -> a hard structured_conflict (payload is preferred over value/object)."""
    red = _claim(
        agent_id="agent_red",
        semantic_key="network.port",
        assertion="The app listens on the configured port.",
        value="ignored-when-payload-present",
        payload={"port": 3000},
    )
    blue = _claim(
        agent_id="agent_blue",
        semantic_key="network.port",
        assertion="The app listens on the configured port.",
        payload={"port": 8080},
    )
    discs = ReBattleArena.detect_discrepancies(
        [
            AgentClaimSet(agent_id="agent_red", perspective="u", claims=[red]),
            AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[blue]),
        ]
    )
    assert len(discs) == 1
    assert discs[0].kind == "structured_conflict"


def test_different_prose_same_structured_value_is_semantic_candidate() -> None:
    """Same semantic_key + SAME structured value, differing prose -> a
    semantic_review_candidate (LLM question), NOT a hard conflict.

    This is the case the old logic flagged as a hard discrepancy based on
    divergent prose — a false positive. Python cannot mechanically prove a
    conflict when both agents agree on the value.
    """
    red = _claim(
        agent_id="agent_red",
        semantic_key="cli.command.run",
        assertion="Run the app with make run.",
        value="make run",
    )
    blue = _claim(
        agent_id="agent_blue",
        semantic_key="cli.command.run",
        assertion="Start the service via `make run`.",
        value="make run",
    )
    discs = ReBattleArena.detect_discrepancies(
        [
            AgentClaimSet(agent_id="agent_red", perspective="u", claims=[red]),
            AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[blue]),
        ]
    )
    assert len(discs) == 1
    assert discs[0].kind == "semantic_review_candidate"
    # It is an LLM question, not a hard mechanical conflict.
    assert discs[0].kind != "structured_conflict"


def test_same_value_same_prose_no_discrepancy() -> None:
    """Same semantic_key, same value, same prose -> no discrepancy at all."""
    red = _claim(
        agent_id="agent_red",
        semantic_key="cli.command.run",
        assertion="Run `make run`.",
        value="make run",
    )
    blue = _claim(
        agent_id="agent_blue",
        semantic_key="cli.command.run",
        assertion="Run `make run`.",
        value="make run",
    )
    discs = ReBattleArena.detect_discrepancies(
        [
            AgentClaimSet(agent_id="agent_red", perspective="u", claims=[red]),
            AgentClaimSet(agent_id="agent_blue", perspective="c", claims=[blue]),
        ]
    )
    assert discs == []


def test_lone_inferred_claim_not_open_discrepancy() -> None:
    """A SINGLE inferred/low-confidence claim (no competing agent on the key) is
    undisputed / pending-adjudication. The old confidence heuristic fabricated
    an 'open' Discrepancy; it must now yield ZERO discrepancies and route to
    the Judge instead."""
    lone = _claim(
        agent_id="agent_red",
        semantic_key="config.parameter.port",
        assertion="Port is set in config.",
        value="3000",
        confidence="inferred",
    )
    discs = ReBattleArena.detect_discrepancies(
        [AgentClaimSet(agent_id="agent_red", perspective="u", claims=[lone])]
    )
    assert discs == []


def test_unchallenged_claim_never_auto_accepted() -> None:
    """An undisputed claim (no competing agent, no adjudication) must NEVER
    yield ruling='accepted' — only the Judge (an explicit AdjudicationResult)
    creates an accepted consensus."""
    undisputed = _claim(
        agent_id="agent_red",
        semantic_key="cli.command.help",
        assertion="app --help",
        value="app --help",
        confidence="inferred",
    )
    sets = [AgentClaimSet(agent_id="agent_red", perspective="u", claims=[undisputed])]

    # No discrepancies at all (lone claim is not a mechanical discrepancy)...
    assert ReBattleArena.detect_discrepancies(sets) == []

    # ...and consensus leaves it a PENDING AgentClaim with no fabricated ruling.
    consensus = ReBattleArena.synthesize_consensus(sets)
    assert len(consensus) == 1
    assert isinstance(consensus[0], AgentClaim)
    assert not isinstance(consensus[0], AdjudicatedClaim)
    # No AdjudicatedClaim was created anywhere, so no accepted ruling exists.
    adjudicated = [c for c in consensus if isinstance(c, AdjudicatedClaim)]
    assert all(a.ruling != "accepted" for a in adjudicated)


def test_agent_claim_bundle_roundtrip() -> None:
    """One AgentClaimBundle feeds BOTH AgentClaimSet.from_agent_bundle and
    ClaimSet.from_agent_bundle with identical semantic_key / claim_type /
    value — the unified protocol that removes scout format drift."""
    from makewiki_skills.model.claim import ClaimSet as CoreClaimSet

    bundle = AgentClaimBundle(
        project_name="myapp",
        agent_id="agent_red",
        perspective="user_experience",
        claims=[
            AgentClaim(
                claim_id="c1",
                agent_id="agent_red",
                claim_type="command",
                semantic_key="cli.command.run",
                assertion="Run `make run`.",
                value="make run",
            ),
            AgentClaim(
                claim_id="c2",
                agent_id="agent_red",
                claim_type="config",
                semantic_key="config.parameter.port",
                assertion="Port from config.",
                value="3000",
            ),
        ],
    )

    # ReBattle path: the same bundle projects to an AgentClaimSet.
    rebattle_set = AgentClaimSet.from_agent_bundle(bundle)
    assert rebattle_set.agent_id == "agent_red"
    assert rebattle_set.perspective == "user_experience"
    assert [c.semantic_key for c in rebattle_set.claims] == [
        "cli.command.run",
        "config.parameter.port",
    ]

    # Verify path: the same bundle projects to a core ClaimSet (llm_claim).
    claim_set = CoreClaimSet.from_agent_bundle(bundle)
    assert claim_set.project_name == "myapp"
    assert all(c.provenance == "llm_claim" for c in claim_set.claims)
    assert {c.semantic_key for c in claim_set.claims} == {
        "cli.command.run",
        "config.parameter.port",
    }
    assert {c.claim_type for c in claim_set.claims} == {"command", "config"}
    assert {c.object for c in claim_set.claims} == {"make run", "3000"}

    # Both paths surface the same value / claim_type / semantic_key per claim.
    by_key = {c.semantic_key: c for c in claim_set.claims}
    assert by_key["cli.command.run"].object == "make run"
    assert by_key["cli.command.run"].claim_type == "command"
    assert by_key["config.parameter.port"].object == "3000"
    assert by_key["config.parameter.port"].claim_type == "config"
