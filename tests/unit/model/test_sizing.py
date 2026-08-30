"""Unit tests for repository fact census (raw traits extraction)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app

runner = CliRunner()


def test_cli_census_basic_facts(tmp_path: Path) -> None:
    """Project census returns raw facts without tier or orchestration recommendations."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='mini'\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Mini\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("PORT=8080\n", encoding="utf-8")

    result = runner.invoke(app, ["census", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)

    assert data["source_files"] == 1
    assert data["doc_files"] == 1
    assert data["languages"]["python"] == 1
    assert "pyproject.toml" in data["manifests"]
    assert "main.py" in data["entrypoints"]
    assert ".env.example" in data["configs"]
    assert "python" in data["detected_ecosystems"]

    # Invariant: No prescriptive orchestration or tier conclusions
    banned_keys = {"tier", "recommended_subagents", "rebattle_rounds", "strategy", "subagent_budget"}
    assert not (banned_keys & set(data.keys())), f"Census must not emit prescriptive keys: {banned_keys & set(data.keys())}"


def test_cli_census_monorepo_detection(tmp_path: Path) -> None:
    """Project census detects monorepo workspaces and polyglot languages."""
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()
    (packages_dir / "pkg_a").mkdir()
    (packages_dir / "pkg_a" / "package.json").write_text("{}", encoding="utf-8")
    (packages_dir / "pkg_a" / "index.ts").write_text("export const a = 1;\n", encoding="utf-8")
    (packages_dir / "pkg_b").mkdir()
    (packages_dir / "pkg_b" / "go.mod").write_text("module pkg_b\n", encoding="utf-8")
    (packages_dir / "pkg_b" / "main.go").write_text("package main\n", encoding="utf-8")

    result = runner.invoke(app, ["census", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)

    assert data["source_files"] == 2
    assert data["monorepo_shape"]["is_monorepo"] is True
    assert "packages/pkg_a" in data["monorepo_shape"]["workspaces"]
    assert "packages/pkg_b" in data["monorepo_shape"]["workspaces"]
    assert "node" in data["detected_ecosystems"]
    assert "go" in data["detected_ecosystems"]


def test_cli_sizing_alias(tmp_path: Path) -> None:
    """Deprecated sizing alias forwards directly to census."""
    (tmp_path / "main.rs").write_text("fn main() {}\n", encoding="utf-8")

    result = runner.invoke(app, ["sizing", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["source_files"] == 1
    assert data["languages"]["rust"] == 1

