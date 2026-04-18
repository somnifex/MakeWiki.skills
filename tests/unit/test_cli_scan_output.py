"""Tests for explicit scan JSON output, including LLM fallback metadata."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.scanner.evidence_collector import EvidenceCollector

runner = CliRunner()


def test_scan_json_reports_complete_python_scan(minimal_python_cli_dir: Path):
    result = runner.invoke(app, ["scan", str(minimal_python_cli_dir), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scan_status"] == "complete"
    assert payload["collection_mode"] == "python"
    assert payload["llm_scan_required"] is False
    assert payload["fallback_reason"] is None
    assert payload["suggested_job_kind"] is None
    assert payload["detection"]["project_name"] == "mini-cli"


def test_scan_json_reports_explicit_llm_fallback(
    minimal_python_cli_dir: Path,
    monkeypatch,
):
    def fail_collect(self, project_dir, detection):
        raise RuntimeError("scanner import failure")

    monkeypatch.setattr(EvidenceCollector, "collect", fail_collect)

    result = runner.invoke(app, ["scan", str(minimal_python_cli_dir), "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scan_status"] == "fallback_required"
    assert payload["collection_mode"] == "llm-fallback"
    assert payload["llm_scan_required"] is True
    assert "scanner import failure" in payload["fallback_reason"]
    assert payload["suggested_job_kind"] == "llm-scan"
    assert payload["suggested_skill"] == "makewiki-llm-scan"
    assert "write objective evidence shards" in payload["next_step"]
    assert payload["total_facts"] == 0
