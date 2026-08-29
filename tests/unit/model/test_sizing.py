"""Unit tests for project sizing and dynamic subagent budgeting."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app

runner = CliRunner()


def test_cli_sizing_tier_s(tmp_path: Path) -> None:
    """Project with < 15 source files is classified as Tier S (1-2 subagents)."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")

    result = runner.invoke(app, ["sizing", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["tier"] == "Tier S"
    assert data["recommended_subagents"] == 2
    assert data["rebattle_rounds"] == 0


def test_cli_sizing_tier_m(tmp_path: Path) -> None:
    """Project with 15-80 source files is classified as Tier M (3-5 subagents)."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    for i in range(25):
        (src_dir / f"module_{i}.py").write_text(f"def func_{i}(): pass\n", encoding="utf-8")

    result = runner.invoke(app, ["sizing", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["tier"] == "Tier M"
    assert data["recommended_subagents"] == 4
    assert data["rebattle_rounds"] == 1


def test_cli_sizing_tier_l(tmp_path: Path) -> None:
    """Project with > 80 source files is classified as Tier L (5-10 subagents)."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    for i in range(85):
        (src_dir / f"component_{i}.go").write_text(
            f"package main\nfunc F{i}() {{}}\n", encoding="utf-8"
        )

    result = runner.invoke(app, ["sizing", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["tier"] == "Tier L"
    assert data["recommended_subagents"] == 8
    assert data["rebattle_rounds"] == 2
