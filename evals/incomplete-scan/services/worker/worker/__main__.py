"""worker: a nested background process with its own entrypoint + config.

A shallow root-only scan misses this package entirely. It has its own
pyproject.toml, a __main__ entrypoint, and reads WORKER_QUEUE from .env.
"""

from __future__ import annotations

import os


def main() -> int:
    queue = os.environ.get("WORKER_QUEUE", "default")
    print(f"worker draining queue {queue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
