"""squash CLI.

The authoritative interface. ``--workers`` defaults to 2 here; a stale unit
test asserts 4 and must NOT override the source truth.
"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="squash")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="compress files")
    run.add_argument("in", metavar="IN", help="input path")
    run.add_argument("--workers", type=int, default=2, help="worker threads (default: 2)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        # --workers default lives in the parser above (2), NOT in the test.
        print(f"compressing {getattr(args, 'in')} with {args.workers} workers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
