"""LLM rubric-judge protocol test (§6, #25).

The judge protocol is pure *plumbing*: load rubric.yaml, assemble the judge's
input bundle from gold + docs, and validate the judge's returned structured
verdict. Python performs NO semantic reasoning here — a semantic_score appears
only verbatim from the judge's own JSON. These tests lock that boundary in.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.evals import judge

TRAP_REPO = Path("evals/misleading-readme")
TRAP_AMBIG = Path("evals/ambiguous-install")


def test_rubric_metrics_are_the_six_semantic_metrics():
    # The roadmap's metric names must be the protocol's SEMANTIC_METRICS.
    assert judge.SEMANTIC_METRICS == (
        "workflow_correctness",
        "documentation_usefulness",
        "native_language_quality",
        "troubleshooting_correctness",
        "semantic_parity",
        "epistemic_calibration",
    )


def test_load_rubric_from_trap(tmp_path: Path):
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "rubric.yaml").write_text(
        "trap: synth\n"
        "description: sample\n"
        "metrics:\n"
        "  workflow_correctness:\n"
        "    weight: 0.3\n"
        "    required: true\n"
        "  epistemic_calibration:\n"
        "    weight: 0.2\n"
        "scoring:\n"
        "  pass_threshold: 0.8\n"
        "  passes_when: overall >= 0.8\n"
        "  runs: 3\n",
        encoding="utf-8",
    )
    r = judge.load_rubric(trap_dir)
    assert r.trap == "synth"
    assert r.metrics["workflow_correctness"].weight == 0.3
    assert r.metrics["workflow_correctness"].required is True
    assert r.metrics["epistemic_calibration"].weight == 0.2
    assert r.pass_threshold == 0.8
    assert r.runs == 3


def test_real_trap_rubric_drives_judge_weights(tmp_path: Path):
    """The shipped rubrics spell metric names in human form ("Workflow
    Correctness"); the protocol must mechanically map those onto the fixed
    semantic keys so the judge's weights come from the real rubric."""
    # Prepare a run dir with docs for each real trap.
    run_dir = tmp_path / "run"
    docs = run_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "README.md").write_text("# x", encoding="utf-8")
    for trap in (TRAP_REPO, TRAP_AMBIG):
        bundle = judge.assemble_judge_input(trap, run_dir)
        # Every one of the six semantic metrics resolves to a weight from the
        # rubric (via its human-readable name) — never left unset.
        weights = bundle["semantic_metrics"]
        assert set(weights) == set(judge.SEMANTIC_METRICS)
        assert all(isinstance(w, float) for w in weights.values())


def test_assemble_judge_input_is_mechanical(tmp_path: Path):
    """Judge input = gold rubric + docs verbatim. It embeds NO semantic
    verdict of its own — just the raw material for the judge."""
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "rubric.yaml").write_text("trap: synth\nscoring: {}\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    docs = run_dir / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "README.md").write_text("hello", encoding="utf-8")

    bundle = judge.assemble_judge_input(trap_dir, run_dir)
    assert bundle["trap"] == "synth"
    assert bundle["docs"]["README.md"] == "hello"
    assert set(bundle["semantic_metrics"]) == set(judge.SEMANTIC_METRICS)
    assert bundle["mechanical_evidence"] == {}


def test_judge_verdict_round_trip_and_score_for(tmp_path: Path):
    v = judge.JudgeVerdict(
        trap="synth",
        judge_id="judge-1",
        model="fake",
        each=[
            judge.JudgeAreaVerdict(metric="workflow_correctness", score=0.9, note="ok"),
            judge.JudgeAreaVerdict(metric="native_language_quality", score=0.7, note=""),
        ],
        overall=0.85,
    )
    path = judge.save_judge_verdict(tmp_path, v)
    assert path.is_file()
    loaded = judge.load_judge_verdict(tmp_path)
    assert loaded is not None
    assert loaded.score_for("workflow_correctness") == 0.9
    assert loaded.score_for("native_language_quality") == 0.7
    assert loaded.overall == 0.85


def test_no_judge_bundle_means_no_semantic_score(tmp_path: Path):
    # A run that was NOT judged has no judge_bundle.json; aggregation must not
    # invent a semantic rating. load returns None.
    assert judge.load_judge_verdict(tmp_path) is None
    assert not (tmp_path / judge.JUDGE_VERDICT_FILE).exists()


def test_score_values_come_only_from_judge_json(tmp_path: Path):
    """A semantic score is only ever read back from the judge's own JSON — the
    protocol has no path that computes one."""
    v = judge.JudgeVerdict(
        trap="t", judge_id="j", each=[judge.JudgeAreaVerdict(metric="semantic_parity", score=0.5)], overall=0.5
    )
    judge.save_judge_verdict(tmp_path, v)
    loaded = judge.load_judge_verdict(tmp_path)
    assert loaded is not None
    # The verdict's overall and per-metric scores equal the judge's values,
    # byte-for-byte, not a re-derived number.
    assert loaded.overall == 0.5
    assert loaded.score_for("semantic_parity") == 0.5
