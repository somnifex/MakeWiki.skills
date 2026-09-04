"""Contract tests for Phase 3 Agent-Native architecture.

Verifies:
1. OrchestrationState and SearchLedger models and markdown parsing.
2. Cognitive IA boundary (no hardcoded page filename requirements in Python).
3. 10 benchmark eval traps structure and fixtures.
4. Metric scoring and N >= 3 aggregation without semantic heuristics.
5. V3 cognitive artifact slots store LLM-authored artifacts; Python does not
   schedule subtasks or choose which is "ready".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.evals import aggregate, runner, scorer
from makewiki_skills.model.documentation_model import (
    Capability,
    DocumentationModel,
    Persona,
)
from makewiki_skills.model.documentation_plan import (
    DocumentationPlan,
)
from makewiki_skills.model.orchestration_state import (
    AgentRecord,
    ClaimRecord,
    ConflictRecord,
    OrchestrationState,
    ToolFailureRecord,
)
from makewiki_skills.model.page_spec import PageSpec
from makewiki_skills.model.search_ledger import (
    ScoutClaim,
    SearchLedger,
    parse_search_ledger_markdown,
)
from makewiki_skills.model.v3_artifacts import (
    InvestigationPlan,
    RepositoryBrief,
    RepositoryHypothesis,
    SubtaskOutputSpec,
    SubtaskSpec,
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


def test_search_ledger_to_claim_bundle_literal_migration():
    """SearchLedger -> ClaimBundle migrates only literal fields.

    visibility/abstraction are unknown (never inferred), and identity/summary are
    caller-supplied rather than guessed by Python.
    """
    ledger = SearchLedger(
        role="Config & Runtime Scout",
        searched_areas=["src/config", "src/server"],
        claims=[
            ScoutClaim(
                claim_id="cfg_db_host",
                description="Default DB host is localhost",
                evidence_citations=["src/config.py:12"],
                is_conflict=False,
                confidence="high",
            )
        ],
        unresolved=["Whether SSL is enabled by default"],
        recommended_followups=["Recovery Scout for legacy addon"],
    )
    bundle = ledger.to_claim_bundle(
        bundle_id="claims.config-runtime",
        domain="config-runtime",
        producer_subtask="investigate.config-runtime",
        summary="Config and runtime semantics.",
    )

    assert bundle.id == "claims.config-runtime"
    assert bundle.domain == "config-runtime"
    assert bundle.producer_subtask == "investigate.config-runtime"
    assert bundle.summary == "Config and runtime semantics."
    assert len(bundle.claims) == 1
    claim = bundle.claims[0]
    assert claim.id == "cfg_db_host"
    assert claim.statement == "Default DB host is localhost"
    assert claim.semantic_key == "cfg_db_host"
    assert claim.confidence == "high"
    assert claim.visibility == ["unknown"]
    assert claim.abstraction == "unknown"
    assert claim.evidence[0].path == "src/config.py:12"
    assert claim.evidence[0].symbol_or_location == ""
    # B3 requires a non-blank rationale; the legacy conversion records a literal
    # neutral marker (Python cannot invent a semantic rationale).
    assert claim.evidence[0].rationale != ""
    assert bundle.unresolved == ["Whether SSL is enabled by default"]
    assert bundle.recommended_followups == ["Recovery Scout for legacy addon"]
    # Non-literal sources are not force-mapped into semantic slots.
    assert bundle.newly_discovered_areas == []
    assert bundle.scope_expansions == []


def test_search_ledger_to_claim_bundle_defaults_identity_empty():
    """An all-empty call cannot produce a valid completed ClaimBundle.

    Python must not guess bundle identity, and V3-P1-03 forbids emitting an empty
    ClaimBundle as if investigation were complete — so an empty call raises rather
    than silently returning a blank shell.
    """
    ledger = SearchLedger(role="Scout")
    with pytest.raises(ValueError):
        ledger.to_claim_bundle()


def test_search_ledger_to_claim_bundle_requires_identity_and_substance():
    """Migration requires caller-supplied identity/summary and at least one claim /
    unresolved / follow-up — never a blank or content-free bundle."""
    # Blank identity, but substance present via unresolved.
    ledger = SearchLedger(role="Scout", unresolved=["SSL not confirmed"])
    with pytest.raises(ValueError):
        ledger.to_claim_bundle()

    # Full identity but no claims / unresolved / follow-ups.
    ledger2 = SearchLedger(role="Scout")
    with pytest.raises(ValueError):
        ledger2.to_claim_bundle(
            bundle_id="claims.x",
            domain="d",
            producer_subtask="p",
            summary="s",
        )


def test_search_ledger_markdown_parser_unchanged_by_conversion():
    """to_claim_bundle must not alter the Markdown parser round-trip."""
    ledger = SearchLedger(
        role="Config & Runtime Scout",
        claims=[
            ScoutClaim(
                claim_id="cfg_db_host",
                description="Default DB host is localhost",
                evidence_citations=["src/config.py:12"],
            )
        ],
    )
    md = ledger.to_markdown()
    parsed = parse_search_ledger_markdown(md)
    # Conversion is a pure projection; parser output is unaffected by it.
    _ = ledger.to_claim_bundle(
        bundle_id="claims.config-runtime",
        domain="config-runtime",
        producer_subtask="investigate.config-runtime",
        summary="Config and runtime semantics.",
    )
    parsed2 = parse_search_ledger_markdown(ledger.to_markdown())
    assert parsed2 == parsed


def test_orchestration_state_v3_artifact_slots_round_trip():
    """V3 cognitive artifact slots persist LLM-authored artifacts.

    New slots default to empty / None and round-trip with existing fields. They
    only *store* the LLM-authored artifacts — Python does not schedule subtasks
    or decide which is "ready".
    """
    state = OrchestrationState(
        user_goal="Generate V3 documentation",
        repository_brief=RepositoryBrief(
            project_hypothesis=RepositoryHypothesis(
                name="acme-cli", purpose="Manage channels."
            ),
            important_unknowns=["Exact auth model for the admin API."],
        ),
        investigation_plan=InvestigationPlan(
            project_hypothesis="acme-cli",
            no_investigation_reason=(
                "Survey-only round-trip check; no domain investigation needed here."
            ),
        ),
        subtasks=[
            SubtaskSpec(
                id="investigate.channel-management",
                type="investigation",
                goal="Understand channel configuration.",
                expected_output=SubtaskOutputSpec(
                    type="ClaimBundle", id="claims.channel-management"
                ),
                stop_conditions=["Every important claim has evidence."],
            )
        ],
        documentation_model=DocumentationModel(
            personas=[
                Persona(id="operator", name="Operator", goals=["deploy safely"])
            ],
            capabilities=[Capability(id="channel.manage", name="Manage channels")],
        ),
        page_specs=[
            PageSpec(
                page_id="channel-management",
                page_type="concept",
                title_intent="Channel Management",
                user_goal="Understand channel management.",
                audience=["operator"],
                required_sections=["overview"],
            )
        ],
    )
    reloaded = OrchestrationState.from_json(state.to_json())
    assert reloaded == state
    assert reloaded.repository_brief is not None
    assert reloaded.repository_brief.project_hypothesis.name == "acme-cli"
    assert reloaded.investigation_plan is not None
    assert len(reloaded.subtasks) == 1
    assert reloaded.subtasks[0].id == "investigate.channel-management"
    # documentation_model is now a typed DocumentationModel, not a free dict.
    assert reloaded.documentation_model is not None
    assert reloaded.documentation_model.personas[0].name == "Operator"
    assert reloaded.documentation_model.capabilities[0].id == "channel.manage"
    assert reloaded.page_specs[0].page_id == "channel-management"


def test_orchestration_state_v3_slots_default_empty():
    """Default OrchestrationState has empty V3 slots — nothing is scheduled."""
    state = OrchestrationState()
    assert state.repository_brief is None
    assert state.investigation_plan is None
    assert state.subtasks == []
    assert state.documentation_model is None
    assert state.documentation_plan is None
    assert state.page_specs == []


def test_orchestration_state_documentation_plan_slot_is_typed():
    """``documentation_plan`` is a typed DocumentationPlan, not a free dict."""
    from makewiki_skills.model.documentation_plan import (
        DocumentationRelation,
        DocumentationSection,
    )

    state = OrchestrationState(
        documentation_plan=DocumentationPlan(
            sections=[
                DocumentationSection(
                    id="admin-guide",
                    title_intent="Administrator Guide",
                    persona=["admin", "operator"],
                    pages=["admin/channel-management"],
                )
            ],
            relations=[
                DocumentationRelation(
                    from_="admin/channel-management",
                    to="management-api/channels",
                    type="related",
                )
            ],
            rationale=["Operator/admin pages come first."],
        )
    )
    reloaded = OrchestrationState.from_json(state.to_json())
    assert isinstance(reloaded.documentation_plan, DocumentationPlan)
    assert reloaded.documentation_plan is not None
    assert reloaded.documentation_plan.sections[0].id == "admin-guide"
    assert reloaded.documentation_plan.relations[0].type == "related"


def test_orchestration_state_coerces_legacy_documentation_plan_dict():
    """A legacy dict fixture authored against the ``persona`` / ``from`` contract
    is coerced by pydantic into a typed DocumentationPlan (serialization compat)."""
    state = OrchestrationState.model_validate(
        {
            "documentation_plan": {
                "sections": [
                    {
                        "id": "admin-guide",
                        "title_intent": "Administrator Guide",
                        "persona": ["admin"],
                        "pages": ["channel-management"],
                    }
                ],
                "relations": [{"from": "a", "to": "b", "type": "related"}],
            }
        }
    )
    assert isinstance(state.documentation_plan, DocumentationPlan)
    assert state.documentation_plan.sections[0].persona == ["admin"]
    assert state.documentation_plan.relations[0].from_ == "a"


def test_orchestration_state_has_no_scheduler_ready_selector():
    """Python must not expose a scheduler / "ready subtask" selector."""
    import inspect

    from makewiki_skills.model.orchestration_state import OrchestrationState

    members = [name for name, _ in inspect.getmembers(OrchestrationState)]
    assert not any(
        "schedule" in name.lower() or "ready" in name.lower() or "select" in name.lower()
        for name in members
    )


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
