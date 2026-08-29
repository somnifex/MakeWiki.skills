"""Main launcher entrypoint for MakeWiki.skills."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from makewiki_skills.cli import app

if __name__ == "__main__":
    app()
