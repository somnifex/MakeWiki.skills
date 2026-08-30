#!/usr/bin/env python3
"""Aggregate N >= 3 runs of one eval trap.

Usage:
    python evals/aggregate.py <trap> [--runs-root PATH]

Delegates to ``makewiki_skills.evals.runner``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from makewiki_skills.evals import runner

HERE = Path(__file__).resolve().parent
DEFAULT_RUNS_ROOT = HERE / "runs"


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: aggregate.py <trap> [--runs-root PATH]")
        return 2
    trap = args[0]
    runs_root = DEFAULT_RUNS_ROOT
    if "--runs-root" in args:
        idx = args.index("--runs-root")
        runs_root = Path(args[idx + 1]).resolve()
    agg = runner.aggregate(runs_root, trap, trap_dir=HERE / trap)
    print(f"trap={agg.trap} runs={agg.n_runs} (N>=3: {agg.n_satisfied})")
    print(f"  overall_pass_rate={agg.overall_pass_rate}")
    print(f"  mean_mechanical_pass={agg.mean_mechanical_pass} variance={agg.variance}")
    print(f"  required_claim_recall={agg.required_claim_recall}")
    print(f"  unsupported_claim_rate={agg.unsupported_claim_rate}")
    print(f"  unknown_discipline_rate={agg.unknown_discipline_rate}")
    if agg.common_failure_classes:
        print(f"  common_failure_classes={', '.join(agg.common_failure_classes)}")
    for m in agg.metric_aggregates:
        print(f"  metric {m.name}: pass_rate={m.pass_rate} ({m.passed}/{m.total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
