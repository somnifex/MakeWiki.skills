"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "projects"


@pytest.fixture
def minimal_python_cli_dir() -> Path:
    return FIXTURES_DIR / "minimal-python-cli"


@pytest.fixture
def minimal_node_app_dir() -> Path:
    return FIXTURES_DIR / "minimal-node-app"


@pytest.fixture
def sample_python_cli_dir() -> Path:
    return Path(__file__).parent.parent / "examples" / "sample-python-cli"


@pytest.fixture
def sample_node_app_dir() -> Path:
    return Path(__file__).parent.parent / "examples" / "sample-node-app"
