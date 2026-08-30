"""prepare / score / aggregate orchestration for MakeWiki evals.

Host-agnostic entry point used by ``evals/run_evals.py`` (and the thin
``score_run.py`` / ``aggregate.py`` wrappers). Three stages:

* ``prepare`` — copy a trap repo into a clean run dir (and, with ``--fixture``,
  lay down a deterministic fake-LLM run bundle so the mechanical harness is
  fully exercisable without a model host).
* ``score``   — deterministically score one run bundle against the trap golds.
* ``aggregate`` — roll N >= 3 run bundles + any LLM-judge bundles into one
  aggregate.

``check_fixtures`` preserves the historical gold-file completeness check so a
trap that isn't ready to run is reported before scoring.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from . import aggregate as aggregate_mod
from . import artifact
from . import scorer as scorer_mod

DEFAULT_RUNS_ROOT = "evals/runs"


# ---------------------------------------------------------------------------
# Fixture completeness (the historical gold-file checklist, kept)
# ---------------------------------------------------------------------------

REQUIRED_GOLD = (
    "README.md",
    "verified_facts.json",
    "required_claims.json",
    "forbidden_claims.json",
    "expected_unknowns.json",
    "rubric.yaml",
)
JSON_GOLD = (
    "verified_facts.json",
    "required_claims.json",
    "forbidden_claims.json",
    "expected_unknowns.json",
)


def fixture_status(trap_dir: Path) -> tuple[list[str], list[str]]:
    """Return (missing, malformed) gold files for a trap directory."""
    missing = [f for f in REQUIRED_GOLD if not (trap_dir / f).is_file()]
    malformed: list[str] = []
    for gold in JSON_GOLD:
        path = trap_dir / gold
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8") as fh:
                json.load(fh)
        except Exception:  # noqa: BLE001 - report any parse failure
            malformed.append(gold)
    return missing, malformed


def check_fixtures(evals_root: Path) -> tuple[list[str], list[tuple[str, list[str], list[str]]]]:
    """Check every trap under ``evals_root``.

    Returns (trap_names, incomplete) where each incomplete element is
    (name, missing, malformed).
    """
    traps = sorted(
        d
        for d in evals_root.iterdir()
        if d.is_dir() and not d.name.startswith(".") and (d / "rubric.yaml").is_file()
    )
    incomplete: list[tuple[str, list[str], list[str]]] = []
    for trap in traps:
        missing, malformed = fixture_status(trap)
        if missing or malformed:
            incomplete.append((trap.name, missing, malformed))
    return [t.name for t in traps], incomplete


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------


def prepare(
    trap_dir: Path,
    runs_root: Path,
    *,
    run_id: str | None = None,
    seed: int = 0,
    fixture: bool = False,
    host: str = "",
) -> Path:
    """Prepare a run directory for ``trap_dir``.

    Copies the trap repo into ``runs_root/<trap>/run-<n>/`` so a host can run
    ``/makewiki`` against an isolated copy. With ``fixture=True`` and when the
    trap has a bundled fixture handoff, writes the deterministic run bundle too.
    """
    trap = trap_dir.name
    run_dir = runs_root / trap / (run_id or f"run-{seed}")
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Copy the trap repo (source files only, no gold files) into the run dir
    # as the working repo a host would point /makewiki at.
    repo = run_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    for item in sorted(trap_dir.iterdir()):
        if item.name in REQUIRED_GOLD or item.name in JSON_GOLD:
            continue
        if item.is_dir():
            shutil.copytree(item, repo / item.name)
        else:
            shutil.copy2(item, repo / item.name)

    if fixture:
        fixture_bundle = _fixture_bundle(trap, run_dir, seed=seed, host=host)
        if fixture_bundle is not None:
            _write_fixture_bundle(run_dir, fixture_bundle, run_id=run_dir.name, host=host)
    return run_dir


# ---------------------------------------------------------------------------
# The deterministic fake-LLM run bundle (hostless eval)
# ---------------------------------------------------------------------------


def _fixture_bundle(trap: str, run_dir: Path, *, seed: int, host: str) -> dict[str, Any] | None:
    """Build a deterministic fake-LLM bundle for ``trap``, or None if unseen.

    This represents the ARTIFACTS a correct run would produce: the incoming
    Scout claim(s), a ReBattle discrepancy, the Judge accepting the stronger
    evidence, and (for the handled traps) a mechanical report / gate state that
    the real pipeline would confirm. It is used only to exercise the harness
    offline; the authoritative integration test drives the REAL Python plane.
    """
    from . import fixtures_bundles

    return {
        "misleading-readme": fixtures_bundles.MISLEADING_README,
        "ambiguous-install": fixtures_bundles.AMBIGUOUS_INSTALL,
        "hidden-entrypoints": fixtures_bundles.HIDDEN_ENTRYPOINTS,
        "indirect-config": fixtures_bundles.INDIRECT_CONFIG,
        "stale-readme": fixtures_bundles.STALE_README,
        "monorepo-discovery": fixtures_bundles.MONOREPO_DISCOVERY,
    }.get(trap)


def _write_fixture_bundle(
    run_dir: Path, bundle: dict[str, Any], *, run_id: str | None = None, host: str | None = None
) -> None:
    meta = artifact.RunMeta(
        trap=bundle["trap"],
        run_id=str(run_id or bundle.get("run_id", "fixture")),
        seed=bundle.get("seed", 0),
        host=str(host or bundle.get("host", "fixture")),
        executed_by="fixture",
    )
    docs = bundle.get("docs", {})
    docs_dir = artifact.docs_dir_for(run_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name, content in docs.items():
        (docs_dir / name).write_text(content, encoding="utf-8")

    artifacts: dict[str, BaseModel] = {
        "evidence.json": artifact.EvidenceArtifact.model_validate(bundle["evidence"]),
        "agent_claims.json": artifact.AgentClaimsArtifact.model_validate(bundle["agent_claims"]),
        "rebattle.json": artifact.RebattleArtifact.model_validate(bundle["rebattle"]),
        "adjudications.json": artifact.AdjudicationsArtifact.model_validate(bundle["adjudications"]),
        "semantic_model.json": artifact.SemanticModelArtifact.model_validate(bundle["semantic_model"]),
        "semantic_audit.json": artifact.SemanticAuditArtifact.model_validate(bundle["semantic_audit"]),
        "mechanical_report.json": artifact.MechanicalReportArtifact.model_validate(
            bundle["mechanical_report"]
        ),
        "quality_gate.json": artifact.QualityGateArtifact.model_validate(bundle["quality_gate"]),
    }
    artifact.save_run(run_dir, meta, artifacts)


# ---------------------------------------------------------------------------
# score / aggregate wrappers
# ---------------------------------------------------------------------------


def score(run_dir: Path, trap_dir: Path) -> scorer_mod.MechanicalScore:
    return scorer_mod.score_run(run_dir, trap_dir)


def aggregate(runs_root: Path, trap: str, trap_dir: Path | None = None) -> aggregate_mod.TrapAggregate:
    """Aggregate N runs of ``trap`` under ``runs_root``.

    ``runs_root`` holds the prepared run directories (``runs_root/<trap>/run-*``);
    ``trap_dir`` is the gold-file directory ``evals/<trap>/``. The gold files are
    NOT copied into the runs root (see :func:`prepare`), so callers must supply
    the real trap dir — falling back to ``runs_root/<trap>`` only preserves the
    legacy behaviour where gold lives alongside runs.
    """
    runs_root = Path(runs_root)
    trap_dir = Path(trap_dir) if trap_dir is not None else runs_root / trap
    run_dirs = [
        d
        for d in sorted(runs_root.glob(f"{trap}/*"))
        if (d / artifact.RUN_INDEX_FILE).is_file()
    ]
    if not run_dirs:
        raise ValueError(f"no runs found for trap {trap!r} under {runs_root}")
    return aggregate_mod.aggregate_runs(run_dirs, trap_dir)
