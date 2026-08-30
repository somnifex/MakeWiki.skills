#!/usr/bin/env python3
"""Score one eval run bundle deterministically.

Usage:
    python evals/score_run.py evals/runs/<trap>/run-0 evals/<trap>
Exit status 0 = mechanical pass, 1 = mechanical failure.

Delegates to ``makewiki_skills.evals.runner``; installed via the repo venv.
"""

from __future__ import annotations

import sys
from pathlib import Path

from makewiki_skills.evals import runner


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("usage: score_run.py <run-dir> <trap-dir>")
        return 2
    run_dir = Path(args[0]).resolve()
    trap_dir = Path(args[1]).resolve()
    score = runner.score(run_dir, trap_dir)
    print(f"trap={score.trap} run={score.run_id} mechanical_pass={score.mechanical_pass}")
    for m in score.metrics:
        mark = "PASS" if m.passed else "FAIL"
        print(f"  [{mark}] {m.name}: {m.detail}")
    return 0 if score.mechanical_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
