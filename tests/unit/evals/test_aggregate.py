"""N >= 3 aggregate protocol test (§7, #26)."""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.evals import aggregate as agg_mod
from makewiki_skills.evals import judge, runner


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
    # The run bundles ground the pkg.dep claim in pyproject.toml; the synthetic
    # trap repo must actually contain that file or the stricter evidence-ref
    # validation (path must exist) rightly flags the ref as invalid and rolls
    # mechanical_pass to False, breaking the pooling assertions.
    (trap_dir / "pyproject.toml").write_text('[project]\nname = "synth"\n', encoding="utf-8")
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


def _write_judge_bundle(run_dir: Path, *, scores: dict[str, float], overall: float) -> Path:
    """Persist an LLM judge verdict bundle into a run directory (judge's API)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    verdict = judge.JudgeVerdict(
        trap="synth",
        judge_id="synthetic-judge",
        each=[judge.JudgeAreaVerdict(metric=k, score=v) for k, v in scores.items()],
        overall=overall,
    )
    return judge.save_judge_verdict(run_dir, verdict)


def test_aggregate_mixed_judge_and_missing_runs(tmp_path: Path):
    """Runs with a judge bundle are summarised; runs without are reported missing,
    never fabricated a score."""
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    # Two runs WITH judge bundles, one WITHOUT.
    _write_run(runs / "run-0")
    _write_run(runs / "run-1")
    _write_run(runs / "run-2")
    _write_judge_bundle(
        runs / "run-0",
        scores={"workflow_correctness": 0.9, "documentation_usefulness": 0.7},
        overall=0.85,
    )
    _write_judge_bundle(
        runs / "run-1",
        scores={"workflow_correctness": 0.7, "documentation_usefulness": 0.9},
        overall=0.75,
    )
    run_dirs = [runs / name for name in ("run-0", "run-1", "run-2")]
    j = agg_mod.aggregate_judge_scores(run_dirs, trap_dir)

    assert j.present_runs == 2
    assert j.missing_runs == 1
    assert j.total_runs == 3

    wf = next(m for m in j.per_metric if m.metric == "workflow_correctness")
    assert wf.judged == 2
    assert wf.missing == 0  # both COMPLETE runs graded it; total scoped to present runs
    assert wf.total == 2
    assert wf.mean == pytest.approx((0.9 + 0.7) / 2)
    assert wf.median == pytest.approx(0.8, abs=1e-3)
    assert wf.min == 0.7
    assert wf.max == 0.9
    # both judged scores (0.9, 0.7) vs default 0.8 threshold: only 0.9 passes.
    assert wf.pass_rate == pytest.approx(0.5, abs=1e-3)

    doc = next(m for m in j.per_metric if m.metric == "documentation_usefulness")
    assert doc.judged == 2
    assert doc.missing == 0
    assert doc.mean == pytest.approx(0.8, abs=1e-3)

    # overall summary aggregates the judge-supplied overalls
    assert j.overall is not None
    assert j.overall.metric == "overall"
    assert j.overall.judged == 2
    assert j.overall.missing == 0
    assert j.overall.mean == pytest.approx(0.8, abs=1e-3)  # (0.85 + 0.75) / 2

    # the run WITHOUT a bundle is reported as a missing run, never given a
    # fabricated score and never folded into the per-metric population.
    assert j.missing_runs == 1
    for metric in ("workflow_correctness", "documentation_usefulness"):
        m = next(x for x in j.per_metric if x.metric == metric)
        assert m.missing == 0
        assert m.judged == m.total == 2
    # metrics no bundle graded at all: judged 0, missing across the present runs.
    untouched = next(x for x in j.per_metric if x.metric == "semantic_parity")
    assert untouched.judged == 0
    assert untouched.missing == 2
    assert untouched.total == 2
    assert untouched.mean == 0.0


def test_aggregate_judge_metric_omitted_from_bundle_counts_as_missing(tmp_path: Path):
    """A run with a judge bundle but missing a specific metric counts toward that
    metric's missing, not judged."""
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    _write_run(runs / "run-0")
    _write_run(runs / "run-1")
    # Only one metric present in each bundle.
    _write_judge_bundle(runs / "run-0", scores={"workflow_correctness": 0.9}, overall=0.9)
    _write_judge_bundle(runs / "run-1", scores={"epistemic_calibration": 0.5}, overall=0.5)
    j = agg_mod.aggregate_judge_scores([runs / "run-0", runs / "run-1"], trap_dir)

    wf = next(m for m in j.per_metric if m.metric == "workflow_correctness")
    assert wf.judged == 1
    assert wf.missing == 1  # run-1 has a bundle but no workflow_correctness
    assert wf.total == 2
    assert wf.mean == pytest.approx(0.9)
    assert wf.stddev == 0.0  # single judged run
    assert wf.median == pytest.approx(0.9)

    ec = next(m for m in j.per_metric if m.metric == "epistemic_calibration")
    assert ec.judged == 1
    assert ec.missing == 1


def test_aggregate_no_judge_bundles_at_all(tmp_path: Path):
    """With no judge bundles, nothing is fabricated: present_runs 0, all judged 0,
    overall None."""
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    for name in ("run-0", "run-1", "run-2", "run-3"):
        _write_run(runs / name)
    j = agg_mod.aggregate_judge_scores(
        [runs / name for name in ("run-0", "run-1", "run-2", "run-3")], trap_dir
    )
    assert j.present_runs == 0
    assert j.missing_runs == 4
    assert j.total_runs == 4
    assert j.overall is None
    for m in j.per_metric:
        # Scoped to the complete present run population (here, none), so no
        # metric reports any judged/missing/total; the 4 absent runs surface as
        # missing_runs on the aggregate, not fabricated per-metric numbers.
        assert m.judged == 0
        assert m.missing == 0
        assert m.total == 0
        assert m.mean == 0.0
        assert m.median == 0.0
        assert m.stddev == 0.0
        assert m.min == 0.0
        assert m.max == 0.0


def test_aggregate_runs_wires_judge_aggregate(tmp_path: Path):
    """aggregate_runs populates the new judge field from the same run_dirs."""
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    for name in ("run-0", "run-1", "run-2"):
        _write_run(runs / name)
    _write_judge_bundle(runs / "run-0", scores={"workflow_correctness": 0.6}, overall=0.6)
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    assert a.judge.present_runs == 1
    assert a.judge.missing_runs == 2
    assert a.judge.total_runs == 3
    wf = next(m for m in a.judge.per_metric if m.metric == "workflow_correctness")
    assert wf.judged == 1
    assert wf.mean == pytest.approx(0.6)
    # pass_rate vs default threshold 0.8: 0.6 fails, so 0.
    assert wf.pass_rate == 0.0


def test_aggregate_runs_judge_defaults_to_empty_when_no_bundle(tmp_path: Path):
    """Existing mechanical aggregate still works with no judge bundles: the judge
    field defaults to an empty/zero aggregate."""
    trap_dir = _write_gold(tmp_path)
    runs = tmp_path / "runs" / "synth"
    for name in ("run-0", "run-1", "run-2"):
        _write_run(runs / name, required_found=True)
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    assert a.judge.present_runs == 0
    assert a.judge.missing_runs == 3
    assert a.required_claim_recall == 1.0  # mechanical path unaffected


def test_aggregate_judge_pass_rate_uses_rubric_threshold(tmp_path: Path):
    """pass_rate is computed against the rubric's pass_threshold, not hardcoded."""
    trap_dir = _write_gold(tmp_path)
    # Write a rubric with a custom (low) pass threshold.
    (trap_dir / "rubric.yaml").write_text(
        "trap: synth\nscoring: {pass_threshold: 0.5}\n", encoding="utf-8"
    )
    runs = tmp_path / "runs" / "synth"
    _write_run(runs / "run-0")
    _write_run(runs / "run-1")
    _write_run(runs / "run-2")
    _write_judge_bundle(
        runs / "run-0", scores={"workflow_correctness": 0.3}, overall=0.3
    )
    _write_judge_bundle(
        runs / "run-1", scores={"workflow_correctness": 0.7}, overall=0.7
    )
    j = agg_mod.aggregate_judge_scores(
        [runs / name for name in ("run-0", "run-1", "run-2")], trap_dir
    )
    wf = next(m for m in j.per_metric if m.metric == "workflow_correctness")
    # threshold 0.5: 0.7 passes, 0.3 fails -> 1/2 judged pass.
    assert wf.pass_rate == pytest.approx(0.5, abs=1e-3)
    assert wf.judged == 2
    assert wf.missing == 0
    assert wf.total == 2  # both complete runs graded it; run-2 (no bundle) excluded


def _write_required_rubric(trap_dir: Path) -> None:
    """Writer a rubric that marks workflow_correctness as a REQUIRED metric."""
    (trap_dir / "rubric.yaml").write_text(
        "trap: synth\n"
        "metrics:\n"
        "  workflow_correctness:\n"
        "    weight: 0.4\n"
        "    required: true\n"
        "  documentation_usefulness:\n"
        "    weight: 0.3\n"
        "    required: false\n"
        "scoring:\n"
        "  pass_threshold: 0.8\n",
        encoding="utf-8",
    )


def test_required_metric_omission_marks_bundle_incomplete(tmp_path: Path):
    """A judge bundle missing a REQUIRED rubric metric is classified incomplete,
    never an ordinary present run and never an ordinary optional-missing."""
    trap_dir = _write_gold(tmp_path)
    _write_required_rubric(trap_dir)
    runs = tmp_path / "runs" / "synth"
    # run-0: complete (has the required metric). run-1: bundle omits the required
    # workflow_correctness. run-2: no bundle at all.
    _write_run(runs / "run-0")
    _write_run(runs / "run-1")
    _write_run(runs / "run-2")
    _write_judge_bundle(
        runs / "run-0",
        scores={"workflow_correctness": 0.9, "documentation_usefulness": 0.7},
        overall=0.85,
    )
    _write_judge_bundle(
        runs / "run-1",
        scores={"documentation_usefulness": 0.9},
        overall=0.9,
    )
    j = agg_mod.aggregate_judge_scores(
        [runs / name for name in ("run-0", "run-1", "run-2")], trap_dir
    )

    # run-0 is complete, run-1 is incomplete (required metric missing), run-2 missing.
    assert j.present_runs == 1
    assert j.incomplete_runs == 1
    assert j.missing_runs == 1
    assert j.total_runs == 3
    assert len(j.incomplete_run_ids) == 1

    # The required metric is graded once (run-0); the incomplete + missing runs
    # are excluded from the (present-run-scoped) distribution.
    wf = next(m for m in j.per_metric if m.metric == "workflow_correctness")
    assert wf.judged == 1
    assert wf.missing == 0
    assert wf.total == 1
    assert wf.mean == pytest.approx(0.9)

    # An optional metric graded ONLY in the incomplete run is NOT pooled into the
    # statistics: run-1's judgment cannot be treated as ordinary, so its 0.9
    # must not shift the distribution of the single complete run (run-0's 0.7).
    doc = next(m for m in j.per_metric if m.metric == "documentation_usefulness")
    assert doc.judged == 1  # run-0 only; run-1's incomplete value excluded
    assert doc.missing == 0  # no complete run skipped it
    assert doc.total == 1
    assert doc.mean == pytest.approx(0.7)  # NOT (0.7 + 0.9) / 2

    assert j.overall is not None
    assert j.overall.judged == 1  # run-0 only; run-1's overall excluded
    assert j.overall.missing == 0
    assert j.overall.mean == pytest.approx(0.85)


def test_required_metric_present_in_all_bundles_is_not_incomplete(tmp_path: Path):
    """When every judge bundle supplies the required metric, no run is incomplete."""
    trap_dir = _write_gold(tmp_path)
    _write_required_rubric(trap_dir)
    runs = tmp_path / "runs" / "synth"
    for name in ("run-0", "run-1"):
        _write_run(runs / name)
        _write_judge_bundle(
            runs / name,
            scores={"workflow_correctness": 0.8, "documentation_usefulness": 0.6},
            overall=0.8,
        )
    j = agg_mod.aggregate_judge_scores([runs / "run-0", runs / "run-1"], trap_dir)
    assert j.present_runs == 2
    assert j.incomplete_runs == 0
    assert j.missing_runs == 0


def test_required_metric_omission_wires_into_aggregate_runs(tmp_path: Path):
    """aggregate_runs surfaces incomplete runs through the judge aggregate."""
    trap_dir = _write_gold(tmp_path)
    _write_required_rubric(trap_dir)
    runs = tmp_path / "runs" / "synth"
    for name in ("run-0", "run-1", "run-2"):
        _write_run(runs / name)
    _write_judge_bundle(
        runs / "run-0", scores={"workflow_correctness": 0.8}, overall=0.8
    )
    # run-1 and run-2 omit the required workflow_correctness.
    _write_judge_bundle(runs / "run-1", scores={"documentation_usefulness": 0.5}, overall=0.5)
    _write_judge_bundle(runs / "run-2", scores={"documentation_usefulness": 0.6}, overall=0.6)
    a = agg_mod.aggregate_runs([runs / name for name in ("run-0", "run-1", "run-2")], trap_dir)
    assert a.judge.present_runs == 1
    assert a.judge.incomplete_runs == 2
    assert a.judge.missing_runs == 0
    assert a.judge.total_runs == 3
