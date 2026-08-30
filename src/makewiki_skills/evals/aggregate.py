"""N >= 3 aggregation across repeated runs of one trap.

An eval trap must be run at least three times; this module rolls the per-run
mechanical scores up into a single aggregate. All aggregation is mechanical
summarization of already-scored structured fields — it adds no new semantic
judgment.

The LLM Eval-Judge's §6 semantic verdict bundles (:mod:`judge`) are deliberately
NOT rolled up here: each judge bundle is an independent LLM judgment per run
(workflow correctness, native-language quality, ...) and Python never averages
or aggregates them without a host driving real judge runs. They are persisted
per run (``save_judge_verdict``) for downstream host/orchestration consumption;
this module aggregates only the deterministic mechanical metrics.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, Field

from . import scorer

# Minimum runs before an aggregate is considered N-satisfying.
MIN_RUNS = 3


class MetricAggregate(BaseModel):
    name: str
    pass_rate: float = 0.0  # fraction of runs where the metric passed
    passed: int = 0
    total: int = 0


class TrapAggregate(BaseModel):
    """Aggregate over N runs of a single trap."""

    trap: str
    n_runs: int
    n_satisfied: bool
    overall_pass_rate: float = 0.0
    mean_mechanical_pass: float = 0.0
    variance: float = 0.0
    required_claim_recall: float = 0.0  # pooled found / pooled total
    unsupported_claim_rate: float = 0.0  # pooled forbidden violations / runs
    unknown_discipline_rate: float = 0.0  # pooled broken / runs
    common_failure_classes: list[str] = Field(default_factory=list)
    metric_aggregates: list[MetricAggregate] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)


def aggregate_runs(run_dirs: Iterable[Path], trap_dir: Path) -> TrapAggregate:
    """Aggregate mechanical scores across ``run_dirs`` (N >= 1; warns on < 3).

    ``trap_dir`` is ``evals/<trap>/``. Every run is scored fresh here via
    :func:`scorer.score_run`.
    """
    run_dirs = list(run_dirs)
    if not run_dirs:
        raise ValueError("aggregate_runs requires at least one run directory")

    scores = [scorer.score_run(r, trap_dir) for r in run_dirs]
    run_ids = [s.run_id for s in scores]

    n = len(scores)
    overall = sum(1 for s in scores if s.mechanical_pass) / n

    # pooled required-claim recall = found / total across all runs
    found_sum = sum(s.required_recall[0] for s in scores)
    total_sum = sum(s.required_recall[1] for s in scores)
    req_recall = found_sum / total_sum if total_sum else 0.0

    unsup_rate = sum(s.unsupported_claim_count for s in scores) / n
    unknown_rate = sum(s.unknown_discipline_broken for s in scores) / n

    # variance of the per-run boolean mechanical pass (0/1)
    bits = [1.0 if s.mechanical_pass else 0.0 for s in scores]
    variance = statistics.pvariance(bits) if n > 1 else 0.0

    # per-metric pass-rate rollup
    metric_names: list[str] = []
    for s in scores:
        for m in s.metrics:
            if m.name not in metric_names:
                metric_names.append(m.name)
    metric_aggs: list[MetricAggregate] = []
    for name in metric_names:
        passed = sum(1 for s in scores for m in s.metrics if m.name == name and m.passed)
        total = sum(1 for s in scores for m in s.metrics if m.name == name)
        metric_aggs.append(
            MetricAggregate(
                name=name,
                pass_rate=passed / total if total else 0.0,
                passed=passed,
                total=total,
            )
        )

    # common failure classes: metrics that failed in >= 1 run, ordered by frequency
    failure_counter: dict[str, int] = {}
    for s in scores:
        for m in s.metrics:
            if not m.passed:
                failure_counter[m.name] = failure_counter.get(m.name, 0) + 1
    common = sorted(failure_counter, key=lambda k: (-failure_counter[k], k))

    return TrapAggregate(
        trap=Path(trap_dir).name,
        n_runs=n,
        n_satisfied=n >= MIN_RUNS,
        overall_pass_rate=round(overall, 4),
        mean_mechanical_pass=round(overall, 4),
        variance=round(variance, 4),
        required_claim_recall=round(req_recall, 4),
        unsupported_claim_rate=round(unsup_rate, 4),
        unknown_discipline_rate=round(unknown_rate, 4),
        common_failure_classes=common,
        metric_aggregates=metric_aggs,
        run_ids=run_ids,
    )
