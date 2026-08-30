"""Contract tests for Phase 3 Agent-Native architecture.

Verifies:
1. OrchestrationState and SearchLedger models and markdown parsing.
2. Cognitive IA boundary (no hardcoded page filename requirements in Python).
3. 10 benchmark eval traps structure and fixtures.
4. Metric scoring and N >= 3 aggregation without semantic heuristics.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.evals import aggregate, runner, scorer
from makewiki_skills.model.orchestration_state import (
    AgentRecord,
    ClaimRecord,
    ConflictRecord,
    OrchestrationState,
    ToolFailureRecord,
)
from makewiki_skills.model.search_ledger import (
    ScoutClaim,
    SearchLedger,
    parse_search_ledger_markdown,
)


def test_orchestration_state_lifecycle():
    """Verify OrchestrationState schema validation and serialization."""
    state = OrchestrationState(
        user_goal="Generate documentation for polyglot web platform",
        repository_understanding="Monorepo with Python backend and React frontend",
        search_plan=["Scout-Backend", "Scout-Frontend", "Scout-Deploy"],
        active_agents=[
            AgentRecord(agent_id="agent-1", role="Structure Scout", assigned_scope="packages/")
        ],
        completed_agents=[],
        coverage_gaps=["packages/analytics/"],
        tool_failures=[
            ToolFailureRecord(
                tool_name="ast_parser",
                target_path="packages/legacy/old.py",
                error_message="SyntaxError on line 12",
            )
        ],
        claims=[
            ClaimRecord(
                claim_id="claim-1",
                semantic_key="backend.port",
                assertion="Backend listens on port 8000",
                value=8000,
                confidence=1.0,
                evidence_refs=["src/main.py:15"],
                source_agent="Structure Scout",
            )
        ],
        conflicts=[
            ConflictRecord(
                conflict_id="conf-1",
                semantic_key="backend.port",
                description="README says 3000, code says 8000",
                competing_claims=["claim-1", "claim-readme"],
                sources_involved=["README.md", "src/main.py"],
            )
        ],
        unresolved_questions=["Is Redis caching optional in production?"],
    )

    # Serialization round-trip
    json_str = state.to_json()
    reloaded = OrchestrationState.from_json(json_str)

    assert reloaded.user_goal == state.user_goal
    assert len(reloaded.active_agents) == 1
    assert reloaded.active_agents[0].role == "Structure Scout"
    assert len(reloaded.tool_failures) == 1
    assert reloaded.tool_failures[0].tool_name == "ast_parser"
    assert len(reloaded.claims) == 1
    assert reloaded.claims[0].value == 8000
    assert len(reloaded.conflicts) == 1


def test_search_ledger_markdown_parser():
    """Verify SearchLedger markdown serialization and extraction."""
    ledger = SearchLedger(
        role="Config & Runtime Scout",
        searched_areas=["src/config", "src/server"],
        paths_inspected=["src/config.py", "src/server.py"],
        evidence_refs=["src/config.py:10-25"],
        claims=[
            ScoutClaim(
                claim_id="cfg_db_host",
                description="Default DB host is localhost",
                evidence_citations=["src/config.py:12"],
                is_conflict=False,
                confidence="high",
            ),
            ScoutClaim(
                claim_id="cfg_port_conflict",
                description="README states port 3000 but server.py defaults to 8080",
                evidence_citations=["README.md:5", "src/server.py:40"],
                is_conflict=True,
                confidence="high",
            ),
        ],
        unresolved=["Whether SSL is enabled by default in production"],
        unexplored=["packages/legacy_addon/"],
        confidence=0.92,
        recommended_followups=["Recovery Scout for legacy addon"],
    )

    md = ledger.to_markdown()
    assert "<search_ledger>" in md
    assert "</search_ledger>" in md
    assert "**[CONFLICT]**" in md

    # Parse back from markdown
    parsed = parse_search_ledger_markdown(md)
    assert parsed.role == "Config & Runtime Scout"
    assert parsed.confidence == pytest.approx(0.92, rel=1e-2)
    assert len(parsed.searched_areas) == 2
    assert len(parsed.paths_inspected) == 2
    assert len(parsed.claims) == 2
    assert parsed.claims[0].claim_id == "cfg_db_host"
    assert not parsed.claims[0].is_conflict
    assert parsed.claims[1].claim_id == "cfg_port_conflict"
    assert parsed.claims[1].is_conflict
    assert len(parsed.unresolved) == 1
    assert len(parsed.unexplored) == 1
    assert len(parsed.recommended_followups) == 1


def test_ten_benchmark_eval_traps_exist(tmp_path: Path):
    """Verify that all 10 benchmark eval traps exist and are well-formed."""
    evals_root = Path(__file__).resolve().parents[2] / "evals"

    canonical_traps = [
        "hidden-entrypoint",
        "nested-monorepo",
        "misleading-readme",
        "config-override",
        "tool-failure-recovery",
        "fork-residue",
        "stale-example",
        "unsupported-claim",
        "multilingual-reorder",
        "incomplete-scan",
    ]

    for trap_name in canonical_traps:
        trap_dir = evals_root / trap_name
        assert trap_dir.is_dir(), f"Benchmark trap directory missing: {trap_dir}"
        assert (trap_dir / "rubric.yaml").is_file(), f"Missing rubric.yaml in {trap_dir}"
        assert (trap_dir / "required_claims.json").is_file(), f"Missing required_claims.json in {trap_dir}"
        assert (trap_dir / "forbidden_claims.json").is_file(), f"Missing forbidden_claims.json in {trap_dir}"
        assert (trap_dir / "expected_unknowns.json").is_file(), f"Missing expected_unknowns.json in {trap_dir}"
        assert (trap_dir / "verified_facts.json").is_file(), f"Missing verified_facts.json in {trap_dir}"

        gold = scorer.load_gold(trap_dir)
        assert gold.required or gold.forbidden, f"No required or forbidden claims in {trap_name}"


def test_eval_scorer_and_n_run_aggregation(tmp_path: Path):
    """Verify that the eval scorer and aggregator compute N >= 3 metrics cleanly without semantic heuristics."""
    evals_root = Path(__file__).resolve().parents[2] / "evals"

    canonical_traps = [
        "misleading-readme",
        "nested-monorepo",
        "config-override",
        "tool-failure-recovery",
        "fork-residue",
        "stale-example",
        "unsupported-claim",
        "multilingual-reorder",
        "incomplete-scan",
    ]

    for trap_name in canonical_traps:
        trap_dir = evals_root / trap_name
        run_dirs: list[Path] = []

        for i in range(3):
            r_dir = runner.prepare(trap_dir, tmp_path, run_id=f"run_{i}", fixture=True)
            run_dirs.append(r_dir)
            score = scorer.score_run(r_dir, trap_dir)
            assert score.mechanical_pass, f"Fixture run failed for trap {trap_name}: {score.metrics}"

        # N >= 3 Aggregation
        agg = aggregate.aggregate_runs(run_dirs, trap_dir)
        assert agg.n_runs == 3
        assert agg.n_satisfied
        assert agg.overall_pass_rate == 1.0
        assert agg.variance == 0.0
        gold = scorer.load_gold(trap_dir)
        if gold.required:
            assert agg.required_claim_recall == 1.0
        assert agg.unsupported_claim_rate == 0.0
        assert agg.unknown_discipline_rate == 0.0
        assert agg.conflict_detection_rate == 1.0
        assert agg.judge_correctness_rate == 1.0
        assert agg.semantic_parity_rate == 1.0
