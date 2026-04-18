"""Tests for explicit scan JSON output, including LLM fallback metadata."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.orchestration.models import ChildSkillReceipt
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


def test_status_json_clears_llm_scan_required_after_scan_job_done(
    minimal_python_cli_dir: Path,
    tmp_path: Path,
    monkeypatch,
):
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    def fail_collect(self, project_dir, detection):
        raise RuntimeError("scanner import failure")

    monkeypatch.setattr(EvidenceCollector, "collect", fail_collect)

    prepare_result = runner.invoke(app, ["prepare", str(project_dir), "--format", "json"])
    assert prepare_result.exit_code == 0
    prepare_payload = json.loads(prepare_result.stdout)
    run_dir = Path(prepare_payload["run_dir"])

    receipt = ChildSkillReceipt(
        job_id="llm-scan",
        status="done",
        artifact_path=str((run_dir / "evidence.index.json").relative_to(project_dir)).replace("\\", "/"),
        trace_path=str((run_dir / "traces" / "llm-scan.json").relative_to(project_dir)).replace("\\", "/"),
        attempt=1,
    )
    receipt_path = run_dir / "receipts" / "llm-scan.1.json"
    receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")

    status_result = runner.invoke(app, ["status", str(project_dir), "--format", "json"])
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)

    assert status_payload["scan_job_status"] == "done"
    assert status_payload["llm_scan_required"] is False


def test_generate_returns_nonzero_when_run_incomplete(
    minimal_python_cli_dir: Path,
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    result = runner.invoke(app, ["generate", str(project_dir)])

    assert result.exit_code == 2
    assert "Run incomplete." in result.stdout
