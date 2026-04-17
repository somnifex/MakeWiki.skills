"""Tests for CLI modes that return file payloads instead of writing directly."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.orchestration.models import PagePlan, RunJob, RunState
from makewiki_skills.orchestration.store import RunLayout

runner = CliRunner()


def test_prepare_returns_evidence_and_state_payloads_by_default(
    minimal_python_cli_dir: Path,
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    result = runner.invoke(
        app,
        ["prepare", str(project_dir), "--format", "json"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    state_path = Path(payload["state_path"])
    evidence_index_path = Path(payload["evidence_index_path"])

    assert payload["write_mode"] == "agent"
    assert payload["resumed"] is False
    assert not state_path.exists()
    assert not evidence_index_path.exists()

    files = {item["relative_path"]: item for item in payload["files"]}
    assert state_path.relative_to(project_dir).as_posix() in files
    assert evidence_index_path.relative_to(project_dir).as_posix() in files
    shard_files = [path for path in files if path.startswith(".makewiki/runs/") and "/evidence/shards/" in path]
    assert shard_files
    state_payload = json.loads(files[state_path.relative_to(project_dir).as_posix()]["content"])
    assert state_payload["run_id"] == payload["run_id"]


def test_prepare_write_run_persists_artifacts_when_requested(
    minimal_python_cli_dir: Path,
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    result = runner.invoke(
        app,
        ["prepare", str(project_dir), "--format", "json", "--write-run"],
    )
    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert Path(payload["state_path"]).exists()
    assert Path(payload["evidence_index_path"]).exists()
    assert "write_mode" not in payload


def test_status_returns_state_update_without_touching_disk_by_default(
    minimal_python_cli_dir: Path,
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    prepare_result = runner.invoke(app, ["prepare", str(project_dir), "--format", "json", "--write-run"])
    assert prepare_result.exit_code == 0
    prepare_payload = json.loads(prepare_result.stdout)

    state_path = Path(prepare_payload["state_path"])
    before = state_path.read_text(encoding="utf-8")

    status_result = runner.invoke(
        app,
        ["status", str(project_dir), "--format", "json"],
    )
    assert status_result.exit_code == 0

    payload = json.loads(status_result.stdout)
    assert state_path.read_text(encoding="utf-8") == before
    assert payload["state_update"]["path"] == str(state_path)
    refreshed = json.loads(payload["state_update"]["content"])
    assert refreshed["run_id"] == prepare_payload["run_id"]
    assert refreshed["job_counts"]


def test_assemble_returns_file_plan_by_default(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN"]
    layout = RunLayout.create(project_dir, config.orchestration.state_dir, "run-1")
    layout.ensure_dirs()

    (layout.page_plans_dir / "configuration.json").write_text(
        PagePlan(
            page_id="configuration",
            output_path="configuration.md",
            kind="global",
            scope="global",
            target_ids=[],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (layout.page_artifacts_dir / "en").mkdir(parents=True, exist_ok=True)
    (layout.page_artifacts_dir / "zh-CN").mkdir(parents=True, exist_ok=True)
    (layout.page_artifacts_dir / "en" / "configuration.md").write_text(
        "# Configuration\n\nUse `SERVER_PORT` for the runtime port{{LOW_CONFIDENCE:src/app.py}}.\n",
        encoding="utf-8",
    )
    (layout.page_artifacts_dir / "zh-CN" / "configuration.md").write_text(
        "# 配置\n\n使用 `SERVER_PORT` 控制运行端口{{LOW_CONFIDENCE:src/app.py}}。\n",
        encoding="utf-8",
    )
    state = RunState(
        run_id="run-1",
        project_root=str(project_dir),
        output_dir="makewiki",
        languages=["en", "zh-CN"],
        default_language="en",
        max_attempts=2,
        jobs=[
            RunJob(
                job_id="page-plan:configuration",
                kind="page-plan",
                page_id="configuration",
                status="done",
            ),
            RunJob(
                job_id="page-write:configuration:en",
                kind="page-write",
                page_id="configuration",
                language_code="en",
                status="done",
            ),
            RunJob(
                job_id="page-write:configuration:zh-CN",
                kind="page-write",
                page_id="configuration",
                language_code="zh-CN",
                status="done",
            ),
        ],
    )
    layout.state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "assemble",
            str(project_dir),
            "--lang",
            "en",
            "--lang",
            "zh-CN",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["write_mode"] == "agent"
    assert not (project_dir / "makewiki").exists()

    files = {item["relative_path"]: item for item in payload["files"]}
    assert "configuration.md" in files
    assert "configuration.zh-CN.md" in files
    assert "index.md" in files
    assert "[^low-1]" in files["configuration.md"]["content"]
    assert "Inferred by fallback scan from `src/app.py`." in files["configuration.md"]["content"]


def test_init_config_returns_yaml_without_creating_file_by_default(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init-config", str(tmp_path), "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config_path = tmp_path.resolve() / "makewiki.config.yaml"
    assert payload["path"] == str(config_path)
    assert payload["written"] is False
    assert "output_dir: makewiki" in payload["content"]
    assert not config_path.exists()


def test_init_config_write_persists_file_when_requested(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init-config", str(tmp_path), "--format", "json", "--write"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    config_path = tmp_path.resolve() / "makewiki.config.yaml"
    assert payload["path"] == str(config_path)
    assert payload["written"] is True
    assert config_path.exists()
