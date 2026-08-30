"""matrix CLI.

Current interface exposes ``matrix run --size N``. The old ``compute --dim``
subcommand was REMOVED; ``examples/demo.md`` still shows it and is stale.
"""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="matrix")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a matrix operation")
    run.add_argument("--size", type=int, default=3, help="matrix size (default: 3)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        print(f"matrix run --size {args.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
