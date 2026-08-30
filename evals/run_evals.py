#!/usr/bin/env python3
"""MakeWiki eval harness — prepare / check / score / aggregate.

Host-agnostic. The host (an agent) runs the authoritative ``/makewiki`` flow on
a prepared trap repo and writes run artifacts; this script mechanically scores
and aggregates them. It never calls an LLM and never judges prose.

Commands:
    check [trap...]                 gold-file completeness check (default).
    prepare <trap>                  prepare an isolated run repo (+ run bundle
                                    with --fixture for host-less evaluation).
    score <run-dir> <trap-dir>      deterministically score one run bundle.
    aggregate <trap>                roll N >= 3 runs of a trap into one aggregate.

Examples:
    python evals/run_evals.py check                     # all traps ready?
    python evals/run_evals.py prepare misleading-readme --fixture
    python evals/run_evals.py score evals/runs/misleading-readme/run-0 evals/misleading-readme
    python evals/run_evals.py aggregate misleading-readme
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from makewiki_skills.evals import runner

HERE = Path(__file__).resolve().parent


def _evals_root() -> Path:
    return HERE


def _runs_root() -> Path:
    return HERE / "runs"


def cmd_check(args: argparse.Namespace) -> int:
    if not hasattr(args, "traps") or not args.traps:
        names, incomplete = runner.check_fixtures(_evals_root())
        traps = names
    else:
        incomplete = []
        traps = []
        for name in args.traps:
            trap_dir = _evals_root() / name
            missing, malformed = runner.fixture_status(trap_dir)
            traps.append(name)
            if missing or malformed:
                incomplete.append((name, missing, malformed))
    bad = 0
    print("MakeWiki evals — gold-file checklist\n")
    for name in traps:
        missing, malformed = runner.fixture_status(_evals_root() / name)
        ok = not missing and not malformed
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {name}")
        for f in missing:
            print(f"        missing: {f}")
        for f in malformed:
            print(f"        invalid: {f}")
        if not ok:
            bad += 1
    print(f"\n{len(traps)} trap(s) checked, {bad} incomplete.")
    return 1 if bad else 0


def cmd_prepare(args: argparse.Namespace) -> int:
    trap_dir = _evals_root() / args.trap
    if not (trap_dir / "rubric.yaml").is_file():
        print(f"No such trap: {args.trap}")
        return 1
    runs_root = Path(args.runs_root).resolve() if args.runs_root else _runs_root()
    n = int(getattr(args, "n", 1) or 1)
    for i in range(n):
        run_dir = runner.prepare(
            trap_dir,
            runs_root,
            run_id=f"run-{i}" if n > 1 else None,
            seed=i,
            fixture=args.fixture,
            host=args.host,
        )
        print(run_dir)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).resolve()
    trap_dir = Path(args.trap_dir).resolve()
    score = runner.score(run_dir, trap_dir)
    print(f"trap={score.trap} run={score.run_id} mechanical_pass={score.mechanical_pass}")
    for m in score.metrics:
        mark = "PASS" if m.passed else "FAIL"
        print(f"  [{mark}] {m.name}: {m.detail}")
        if m.keys:
            print(f"        keys: {', '.join(m.keys)}")
    return 0 if score.mechanical_pass else 1


def cmd_aggregate(args: argparse.Namespace) -> int:
    runs_root = Path(args.runs_root).resolve() if args.runs_root else _runs_root()
    agg = runner.aggregate(runs_root, args.trap, trap_dir=_evals_root() / args.trap)
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
    # LLM Eval-Judge summaries (present only when runs carried judge bundles).
    j = agg.judge
    if j is not None:
        print(
            f"  judge_present={j.present_runs} judge_incomplete={j.incomplete_runs} "
            f"judge_missing={j.missing_runs}/{j.total_runs}"
        )
        for m in j.per_metric:
            print(
                f"  judge[{m.metric}] mean={m.mean} median={m.median} stddev={m.stddev} "
                f"min={m.min} max={m.max} pass_rate={m.pass_rate} "
                f"(judged={m.judged} missing={m.missing})"
            )
        if j.overall is not None:
            o = j.overall
            print(
                f"  judge[overall] mean={o.mean} median={o.median} stddev={o.stddev} "
                f"min={o.min} max={o.max} pass_rate={o.pass_rate} (judged={o.judged})"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_evals.py", description=__doc__)
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="gold-file completeness check")
    p_check.add_argument("traps", nargs="*")

    p_prepare = sub.add_parser("prepare", help="prepare a run repo (+ fixture bundle)")
    p_prepare.add_argument("trap")
    p_prepare.add_argument("--fixture", action="store_true", help="write a fake-LLM run bundle")
    p_prepare.add_argument("--n", type=int, default=1, help="number of runs to prepare")
    p_prepare.add_argument("--runs-root", default=None)
    p_prepare.add_argument("--host", default="", help="host label for a fixture run")

    p_score = sub.add_parser("score", help="score one run bundle")
    p_score.add_argument("run_dir")
    p_score.add_argument("trap_dir")

    p_agg = sub.add_parser("aggregate", help="aggregate N runs of one trap")
    p_agg.add_argument("trap")
    p_agg.add_argument("--runs-root", default=None)

    args = parser.parse_args(argv)
    if not args.command or args.command == "check":
        return cmd_check(args)
    if args.command == "prepare":
        return cmd_prepare(args)
    if args.command == "score":
        return cmd_score(args)
    if args.command == "aggregate":
        return cmd_aggregate(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
