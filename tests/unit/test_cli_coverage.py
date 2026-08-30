"""CLI tests for the `makewiki coverage` command and the coverage field in
the `evidence --format json` bundle."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app


def _fake_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "README.md").write_text("# proj\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "proj"\n[project.scripts]\ncli = "app:main"\n',
        encoding="utf-8",
    )
    (root / "app.py").write_text(
        "import typer\napp = typer.Typer()\n@app.command()\ndef run(): ...\n",
        encoding="utf-8",
    )
    (root / ".env.example").write_text("PORT=8080\n", encoding="utf-8")
    return root


def test_coverage_command_emits_valid_json_with_expected_keys(tmp_path: Path):
    root = _fake_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["coverage", str(root), "--format", "json"])
    assert result.exit_code == 0, result.output

    payload = json.loads(result.stdout)
    for key in [
        "files_discovered",
        "files_by_category",
        "files_inspected_by_tool",
        "files_skipped",
        "ignored_files",
        "entrypoints_found",
        "configs_found",
        "tests_inspected",
        "manifests_found",
        "generated_code_boundaries",
        "uncovered_categories",
        "low_confidence_facts",
        "skipped_due_to_max_files",
    ]:
        assert key in payload, f"missing coverage key: {key}"
    assert payload["files_discovered"] > 0


def test_coverage_command_human_output(tmp_path: Path):
    root = _fake_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["coverage", str(root)])
    assert result.exit_code == 0, result.output
    combined = (result.output or "") + (result.stderr or "")
    assert "Files discovered" in combined


def test_coverage_command_errors_on_non_directory(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["coverage", str(tmp_path / "missing")])
    assert result.exit_code == 1


def test_evidence_json_bundle_embeds_coverage(tmp_path: Path):
    root = _fake_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["evidence", str(root), "--format", "json"])
    assert result.exit_code == 0, result.output

    payload = json.loads(result.stdout)
    assert "coverage" in payload, "evidence JSON must embed the coverage dict"
    assert payload["coverage"]["files_discovered"] > 0
    assert "files_by_category" in payload["coverage"]
