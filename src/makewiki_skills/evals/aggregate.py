"""N >= 3 aggregation across repeated runs of one trap.

An eval trap must be run at least three times; this module rolls the per-run
scores up into a single aggregate. All aggregation is mechanical summarization
of already-scored structured fields — it adds no new semantic judgment.

The LLM Eval-Judge's §6 semantic verdict bundles (:mod:`judge`) ARE mechanically
summarized here when present: for each run that persisted a judge bundle
(``judge_bundle.json``), this module computes the mean / median / stddev /
min / max / pass rate of the judge-supplied per-metric and overall scores, and
reports runs with no judge bundle as *missing*. The cognitive authority boundary
is strict: Python only aggregates scores the LLM judge already produced; it
NEVER computes or fabricates a semantic score itself, and a run without a judge
bundle is counted as missing, never silently scored. When no run has a judge
bundle, the ``JudgeAggregate`` reports ``present_runs == 0`` and an empty/latent
``overall``.
"""

from __future__ import annotations

import statistics
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, Field

from . import judge, scorer

# Minimum runs before an aggregate is considered N-satisfying.
MIN_RUNS = 3


class MetricAggregate(BaseModel):
    name: str
    pass_rate: float = 0.0  # fraction of runs where the metric passed
    passed: int = 0
    total: int = 0


class JudgeMetricSummary(BaseModel):
    """Mechanical summary of one metric's JUDGE-SUPPLIED scores.

    Statistics are computed from the LLM judge's own per-run scores across the
    COMPLETE present runs only; Python never produces a semantic score and never
    pools an incomplete judgment into the distribution. ``missing`` therefore
    covers a complete run that still did not grade this particular (optional)
    metric; runs with no judge bundle at all are reported as ``missing_runs`` on
    the aggregate, and runs whose bundle omitted a required metric as
    ``incomplete_runs`` — neither is folded into these per-metric numbers.
    """

    metric: str
    mean: float = 0.0
    median: float = 0.0
    stddev: float = 0.0
    min: float = 0.0
    max: float = 0.0
    pass_rate: float = 0.0  # fraction of judged runs where score >= rubric pass threshold
    judged: int = 0  # runs that supplied this metric
    missing: int = 0  # runs with no judge bundle at all (or no value for this metric)
    total: int = 0  # runs considered (judged + missing)


class JudgeAggregate(BaseModel):
    """Aggregate of the LLM judge verdicts present across runs.

    Summarises ONLY judge-supplied scores. Runs are classified three ways:
    * ``present_runs`` — a judge bundle that satisfied every required rubric
      metric (a complete, usable judgment);
    * ``incomplete_runs`` — a judge bundle missing one or more REQUIRED rubric
      metrics (its judgment cannot be treated as ordinary — a required metric
      was never graded, which is a distinct failure from an optional absence);
    * ``missing_runs`` — no judge bundle at all.

    No score is ever fabricated for a missing or incomplete run.
    """

    present_runs: int = 0  # complete judge bundles (all required metrics present)
    incomplete_runs: int = 0  # judge bundles missing >= 1 required rubric metric
    missing_runs: int = 0  # runs with no judge bundle
    total_runs: int = 0  # present + incomplete + missing
    per_metric: list[JudgeMetricSummary] = Field(default_factory=list)
    overall: JudgeMetricSummary | None = None  # judge-supplied overall scores, or None if no judge run
    incomplete_run_ids: list[str] = Field(default_factory=list)  # run ids disqualified as incomplete


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
    missed_entrypoint_rate: float = 0.0  # missed entrypoints rate
    conflict_detection_rate: float = 0.0  # ReBattle conflict detection pass rate
    judge_correctness_rate: float = 0.0  # Judge output presence / correctness rate
    workflow_correctness_rate: float = 0.0  # Required workflow presence pass rate
    semantic_parity_rate: float = 0.0  # Stable block parity pass rate
    tool_failure_recovery_rate: float = 0.0  # Tool failure recovery pass rate
    common_failure_classes: list[str] = Field(default_factory=list)
    metric_aggregates: list[MetricAggregate] = Field(default_factory=list)
    run_ids: list[str] = Field(default_factory=list)
    judge: JudgeAggregate = Field(default_factory=JudgeAggregate)


def _summarise(scores: list[float], *, metric: str, total: int, threshold: float) -> JudgeMetricSummary:
    """Mechanical statistics over a small set of judge-supplied scores.

    Population stddev (``statistics.pstdev``) keeps a single data point / empty
    set well-defined: with 0 data points every stat is 0.0; with 1 data point
    mean == median == that score and stddev == 0.0. ``total`` is the number of
    runs considered, so ``missing = total - len(scores)``.
    """
    judged = len(scores)
    missing = total - judged
    if not scores:
        return JudgeMetricSummary(
            metric=metric,
            judged=0,
            missing=missing,
            total=total,
        )
    values = [float(s) for s in scores]
    n = len(values)
    mean = statistics.fmean(values)
    median = statistics.median(values)
    stddev = statistics.pstdev(values) if n > 1 else 0.0
    passed = sum(1 for s in values if s >= threshold)
    return JudgeMetricSummary(
        metric=metric,
        mean=round(mean, 4),
        median=round(median, 4),
        stddev=round(stddev, 4),
        min=min(values),
        max=max(values),
        pass_rate=passed / n,
        judged=judged,
        missing=missing,
        total=total,
    )


def aggregate_judge_scores(run_dirs: Iterable[Path], trap_dir: Path) -> JudgeAggregate:
    """Mechanically summarise the LLM judge verdicts present across ``run_dirs``.

    For each run, :func:`judge.load_judge_verdict` reads the persisted judge
    bundle; a run with none is a *missing* run for every metric and for overall.
    A run whose bundle omits a REQUIRED rubric metric is classified *incomplete*
    (``judge.validate_required_metrics``) — it is counted separately from both
    complete present runs and from missing runs, so a required-metric omission
    can never masquerade as an ordinary optional absence.

    The descriptive statistics (mean / median / stddev / min / max / pass_rate)
    are computed ONLY over the *complete* present runs. An incomplete bundle is
    not pooled into the numbers even when it carries a score: a judgment that
    skipped a required metric cannot be treated as ordinary, so its values are
    counted as neither ``judged`` nor folded into the distribution. Its runs
    surface via ``incomplete_runs`` (and the per-metric ``total``, which counts
    every run in the population). Statistics still come only from the
    judge-supplied scores (never computed by Python); ``pass_rate`` uses the
    rubric's ``pass_threshold`` (default 0.8).
    """
    run_dirs = list(run_dirs)
    rubric = judge.load_rubric(trap_dir)
    threshold = rubric.pass_threshold
    total = len(run_dirs)

    complete: list[judge.JudgeVerdict] = []
    incomplete_ids: list[str] = []
    missing_runs = 0
    for rd in run_dirs:
        v = judge.load_judge_verdict(rd)
        if v is None:
            missing_runs += 1
        elif judge.validate_required_metrics(v, rubric):
            # The bundle omitted a required rubric metric -> incomplete. It is
            # excluded from the score distribution: its judgment cannot be
            # treated as ordinary and must not dilute or shift the population
            # statistics of the usable runs.
            incomplete_ids.append(v.judge_id or rd.name)
        else:
            complete.append(v)
    present_runs = len(complete)
    incomplete_runs = len(incomplete_ids)

    per_metric: list[JudgeMetricSummary] = []
    for metric in judge.SEMANTIC_METRICS:
        scores = [s for v in complete if (s := v.score_for(metric)) is not None]
        per_metric.append(_summarise(scores, metric=metric, total=present_runs, threshold=threshold))

    overall_scores = [v.overall for v in complete]
    overall: JudgeMetricSummary | None = _summarise(
        overall_scores, metric="overall", total=present_runs, threshold=threshold
    )
    if present_runs == 0:
        overall = None

    return JudgeAggregate(
        present_runs=present_runs,
        incomplete_runs=incomplete_runs,
        missing_runs=missing_runs,
        total_runs=total,
        per_metric=per_metric,
        overall=overall,
        incomplete_run_ids=incomplete_ids,
    )


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

    # Specific rollup rates extraction from metric_aggs
    def _rate(name: str) -> float:
        agg = next((m for m in metric_aggs if m.name == name), None)
        return agg.pass_rate if agg else 1.0

    conflict_detection_rate = _rate("rebattle_discrepancy_detected")
    judge_correctness_rate = _rate("judge_output_presence")
    workflow_correctness_rate = _rate("required_workflow_presence")
    semantic_parity_rate = _rate("stable_block_parity")
    tool_failure_recovery_rate = _rate("mechanical_gate_state")
    missed_entrypoint_rate = round(1.0 - req_recall, 4)

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
        missed_entrypoint_rate=missed_entrypoint_rate,
        conflict_detection_rate=round(conflict_detection_rate, 4),
        judge_correctness_rate=round(judge_correctness_rate, 4),
        workflow_correctness_rate=round(workflow_correctness_rate, 4),
        semantic_parity_rate=round(semantic_parity_rate, 4),
        tool_failure_recovery_rate=round(tool_failure_recovery_rate, 4),
        common_failure_classes=common,
        metric_aggregates=metric_aggs,
        run_ids=run_ids,
        judge=aggregate_judge_scores(run_dirs, trap_dir),
    )
