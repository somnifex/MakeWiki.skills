"""N >= 3 aggregate protocol test (§7, #26)."""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.evals import aggregate as agg_mod
from makewiki_skills.evals import runner


def _write_run(run_dir: Path, *, required_found: bool = True) -> Path:
    """Write a trivial, schema-valid run bundle for the synthetic trap."""
    run_dir.mkdir(parents=True, exist_ok=True)
    from makewiki_skills.evals import artifact

    rulings = (
        [
            {
                "topic": "pkg.dep",
                "ruling": "accepted",
                "final_assertion": "4.2.0",
                "verified_via_codebase": True,
                "evidence_refs": ["pyproject.toml"],
                "adjudicator_reasoning": "",
            }
        ]
        if required_found
        else []
    )
    meta = artifact.RunMeta(trap="synth", run_id=run_dir.name)
    artifacts: dict[str, object] = {
        "evidence.json": artifact.EvidenceArtifact(facts=[], detected_packages=[]),
        "agent_claims.json": artifact.AgentClaimsArtifact(sets=[]),
        "rebattle.json": artifact.RebattleArtifact(discrepancies=[]),
        "adjudications.json": artifact.AdjudicationsArtifact(rulings=rulings),
        "semantic_model.json": artifact.SemanticModelArtifact(
            dotenv=[], user_tasks=["install"], troubleshooting=[], provenance={},
            claims=([{"semantic_key": "pkg.dep", "value": "4.2.0"}] if required_found else []),
        ),
        "semantic_audit.json": artifact.SemanticAuditArtifact(auditor="fake", documents_digest="x"),
        "mechanical_report.json": artifact.MechanicalReportArtifact(layers=[], total_checks=0),
        "quality_gate.json": artifact.QualityGateArtifact(
            verdict="passed" if required_found else "failed",
            ci_exit_code=0 if required_found else 3,
            semantic_complete=required_found,
            pending_llm_layers=[],
            mechanical_passed=required_found,
        ),
    }
    artifact.save_run(run_dir, meta, artifacts)  # type: ignore[arg-type]
    return run_dir


def _write_gold(tmp_path: Path) -> Path:
    trap_dir = tmp_path / "synth"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "required_claims.json").write_text(
        '[{"id": "rc_dep", "claim_type": "prerequisite", "semantic_key": "pkg.dep", '
        '"assertion": "dep pinned 4.2.0"}]',
        encoding="utf-8",
    )
    (trap_dir / "forbidden_claims.json").write_text("[]", encoding="utf-8")
    (trap_dir / "expected_unknowns.json").write_text("[]", encoding="utf-8")
    (trap_dir / "verified_facts.json").write_text("[]", encoding="utf-8")
    (trap_dir / "rubric.yaml").write_text("trap: synth\nscoring: {}\n", encoding="utf-8")
    return trap_dir


def test_n_less_than_three_is_not_satisfied(tmp_path: Path):
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    _write_run(runs / "run-0")
    _write_run(runs / "run-1")
    a = agg_mod.aggregate_runs([runs / "run-0", runs / "run-1"], trap_dir)
    assert a.n_runs == 2
    assert not a.n_satisfied


def test_three_runs_are_satisfied_and_pooled_recall(tmp_path: Path):
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    for name in ("run-0", "run-1", "run-2"):
        _write_run(runs / name, required_found=True)
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    assert a.n_runs == 3
    assert a.n_satisfied
    # pooled recall = 3 found / 3 total = 1.0 (the §5 top-level rollup).
    assert a.required_claim_recall == 1.0
    assert a.overall_pass_rate == 1.0
    assert a.mean_mechanical_pass == 1.0
    assert a.variance == 0.0


def test_pooled_recall_is_found_over_total_across_runs(tmp_path: Path):
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    _write_run(runs / "run-0", required_found=True)
    _write_run(runs / "run-1", required_found=True)
    _write_run(runs / "run-2", required_found=False)  # one miss
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    # 2 found / 3 total -> 0.6667, NOT 2/3 averaged per-metric (same here), and
    # overall pass is 2/3 = 0.6667.
    assert a.required_claim_recall == pytest.approx(0.6667, abs=1e-3)
    assert a.overall_pass_rate == pytest.approx(0.6667, abs=1e-3)
    assert a.variance > 0


def test_common_failure_classes_collect_failing_metric_names(tmp_path: Path):
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    _write_run(runs / "run-0", required_found=True)
    _write_run(runs / "run-1", required_found=False)
    _write_run(runs / "run-2", required_found=False)
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    assert "required_claim_recall" in a.common_failure_classes


def test_aggregate_rejects_empty_run_list(tmp_path: Path):
    trap_dir = _write_gold(tmp_path)
    with pytest.raises(ValueError):
        agg_mod.aggregate_runs([], trap_dir)


def test_runner_aggregate_uses_explicit_trap_dir(tmp_path: Path):
    """The gold files live in evals/<trap>, NOT under the runs root; aggregate
    must source them from trap_dir (this was the bug that zeroed recall)."""
    trap_dir = _write_gold(tmp_path)
    runs_root = tmp_path / "runs"
    for name in ("run-0", "run-1", "run-2"):
        _write_run(runs_root / "synth" / name, required_found=True)
    a = runner.aggregate(runs_root, "synth", trap_dir=trap_dir)
    assert a.required_claim_recall == 1.0


def test_metric_aggregates_roll_up_per_run_per_metric(tmp_path: Path):
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    _write_run(runs / "run-0", required_found=True)
    _write_run(runs / "run-1", required_found=True)
    _write_run(runs / "run-2", required_found=False)
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    recall_agg = next(m for m in a.metric_aggregates if m.name == "required_claim_recall")
    assert recall_agg.total == 3
    assert recall_agg.passed == 2
    assert recall_agg.pass_rate == pytest.approx(2 / 3, abs=1e-3)
