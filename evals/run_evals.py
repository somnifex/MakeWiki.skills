#!/usr/bin/env python3
"""Gold-file checklist printer for the MakeWiki evals suite.

Dependency-free: this script just walks each trap under `evals/` and reports
whether all five gold files (plus a README/source) are present, so you can
tell at a glance whether a trap is ready to be run as an LLM agent-behavioral
eval.

Behavioral evals are run N >= 3 times per trap (see evals/README.md,
Section 33): each run drives an LLM agent to write documentation against the
trap repo, then scores the output against the gold files and rubric.

Usage:
    python evals/run_evals.py            # check every trap
    python evals/run_evals.py my-trap    # check one trap only
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# trap name -> list of gold files that must exist
REQUIRED = [
    "README.md",
    "verified_facts.json",
    "required_claims.json",
    "forbidden_claims.json",
    "expected_unknowns.json",
    "rubric.yaml",
]

# gold files that must parse as JSON / YAML-ish (schema spot checks)
JSON_GOLDS = [
    "verified_facts.json",
    "required_claims.json",
    "forbidden_claims.json",
    "expected_unknowns.json",
]


def _check(trap_dir):
    name = os.path.basename(trap_dir)
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(trap_dir, f))]
    parse_errors = []
    for gold in JSON_GOLDS:
        path = os.path.join(trap_dir, gold)
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                json.load(fh)
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            parse_errors.append(f"{gold}: {exc}")
    return name, missing, parse_errors


def main(argv):
    filters = argv[1:]
    traps = sorted(
        d
        for d in os.listdir(HERE)
        if os.path.isdir(os.path.join(HERE, d)) and not d.startswith(".")
        and os.path.exists(os.path.join(HERE, d, "rubric.yaml"))
    )
    if filters:
        traps = [t for t in traps if any(f in t for f in filters)]

    if not traps:
        print(f"No traps matched the filter: {' '.join(filters)}")
        return 1

    bad = 0
    print("MakeWiki evals — gold-file checklist\n")
    for trap in traps:
        name, missing, parse_errors = _check(os.path.join(HERE, trap))
        status = "OK  " if not missing and not parse_errors else "FAIL"
        print(f"[{status}] {name}")
        for f in missing:
            print(f"        missing: {f}")
        for err in parse_errors:
            print(f"        invalid: {err}")
        if missing or parse_errors:
            bad += 1

    print(f"\n{len(traps)} trap(s) checked, {bad} incomplete.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
