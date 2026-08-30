"""prepare/score orchestration test (§4, #23)."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.evals import runner, scorer

TRAP_REPO = Path("evals/misleading-readme")


def test_prepare_copies_repo_and_excludes_gold(tmp_path: Path):
    """prepare() lays down an isolated run repo that excludes gold files (a
    host should never see the answers) and includes the source repo."""
    run_dir = runner.prepare(TRAP_REPO, tmp_path, run_id="run-0", seed=0)
    assert run_dir.is_dir()
    repo = run_dir / "repo"
    assert (repo / "app" / "server.py").is_file()
    # Gold files must NOT leak into the repo a host works on.
    for gold in ("required_claims.json", "forbidden_claims.json", "expected_unknowns.json",
                 "verified_facts.json", "rubric.yaml"):
        assert not (repo / gold).exists(), f"gold leaked: {gold}"


def test_prepare_fixture_writes_run_bundle(tmp_path: Path):
    run_dir = runner.prepare(TRAP_REPO, tmp_path, run_id="run-0", seed=0, fixture=True, host="fake")
    # The bundle is written and scores as a mechanical pass against the trap.
    score = scorer.score_run(run_dir, TRAP_REPO)
    assert score.mechanical_pass, [m for m in score.metrics if not m.passed]
    assert score.run_id == "run-0"


def test_prepare_is_deterministic_across_seeds(tmp_path: Path):
    a = runner.prepare(TRAP_REPO, tmp_path, run_id="run-0", seed=0, fixture=True)
    b = runner.prepare(TRAP_REPO, tmp_path, run_id="run-1", seed=1, fixture=True)
    sa = scorer.score_run(a, TRAP_REPO)
    sb = scorer.score_run(b, TRAP_REPO)
    assert sa.mechanical_pass
    assert sb.mechanical_pass
