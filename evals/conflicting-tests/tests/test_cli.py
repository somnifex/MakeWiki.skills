"""Stale unit test.

Asserts ``--workers`` defaults to 4. This CONTRADICTS the source truth in
``app/cli.py`` (default 2). The test is stale and must NOT override source.
"""

from app.cli import build_parser


def test_workers_default() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "./in"])
    # Stale assertion: the parser actually defaults to 2.
    assert args.workers == 4
