"""Tests for the run store and orchestration state refresh flow."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.orchestration.models import (
    ChildSkillReceipt,
    ModuleIndexItem,
    PageIndexItem,
    SemanticModelIndex,
    WorkflowIndexItem,
)
from makewiki_skills.orchestration.store import RunStore
from makewiki_skills.pipeline.pipeline import Pipeline
from makewiki_skills.scanner.evidence_collector import EvidenceCollector
from makewiki_skills.scanner.project_detector import ProjectDetector


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_receipt(layout, receipt: ChildSkillReceipt) -> None:
    receipt_path = layout.receipts_dir / f"{receipt.job_id.replace(':', '__')}.{receipt.attempt}.json"
    _write_json(receipt_path, receipt.model_dump())


def test_prepare_run_writes_evidence_index_and_initial_jobs(minimal_python_cli_dir: Path, tmp_path: Path):
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.orchestration.resume = False
    detector = ProjectDetector()
    detection = detector.detect(project_dir)
    collected = EvidenceCollector(config).collect(project_dir, detection)

    store = RunStore(config)
    layout, state, evidence_index, resumed = store.prepare_run(detection, collected)

    assert resumed is False
    assert layout.evidence_index_file.is_file()
    assert evidence_index.shard_count > 0
    assert any(job.kind == "surface-card" for job in state.jobs)
    assert any(job.kind == "semantic-root" for job in state.jobs)


def test_refresh_state_adds_semantic_jobs_and_exposes_next_ready_jobs(
    minimal_python_cli_dir: Path,
    tmp_path: Path,
):
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.orchestration.resume = False
    detector = ProjectDetector()
    detection = detector.detect(project_dir)
    collected = EvidenceCollector(config).collect(project_dir, detection)

    store = RunStore(config)
    layout, state, _evidence_index, _resumed = store.prepare_run(detection, collected)

    for job in state.jobs:
        if job.kind != "surface-card" or job.artifact_path is None:
            continue
        artifact_path = project_dir / job.artifact_path
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text('{"surface":"ok"}\n', encoding="utf-8")
        _write_receipt(
            layout,
            ChildSkillReceipt(
                job_id=job.job_id,
                status="done",
                artifact_path=job.artifact_path,
                trace_path=layout.rel_to_project(layout.traces_dir / f"{job.source_ref}.json"),
                attempt=1,
            ),
        )

    semantic_index = SemanticModelIndex(
        run_id=layout.run_id,
        languages=config.languages,
        modules=[ModuleIndexItem(id="core", name="Core")],
        workflows=[WorkflowIndexItem(id="hello-world", name="Hello World", module_ids=["core"])],
        pages=[PageIndexItem(id="commands", kind="global", scope="global", target_ids=[])],
    )
    layout.project_brief_file.write_text('{"name":"mini-cli"}\n', encoding="utf-8")
    layout.semantic_index_file.write_text(semantic_index.model_dump_json(indent=2), encoding="utf-8")
    _write_receipt(
        layout,
        ChildSkillReceipt(
            job_id="semantic-root",
            status="done",
            artifact_path=layout.rel_to_project(layout.semantic_index_file),
            trace_path=layout.rel_to_project(layout.traces_dir / "semantic-root.json"),
            attempt=1,
        ),
    )

    refreshed_state, refreshed_index = store.refresh_state(layout, config.languages)
    ready_job_ids = [job.job_id for job in store.ready_jobs(refreshed_state, limit=10)]

    assert refreshed_index is not None
    assert refreshed_index.modules[0].id == "core"
    assert any(job.job_id == "module-brief:core" for job in refreshed_state.jobs)
    assert "module-brief:core" in ready_job_ids


def test_done_receipt_without_artifact_becomes_stale(minimal_python_cli_dir: Path, tmp_path: Path):
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.orchestration.resume = False
    detector = ProjectDetector()
    detection = detector.detect(project_dir)
    collected = EvidenceCollector(config).collect(project_dir, detection)

    store = RunStore(config)
    layout, _state, _evidence_index, _resumed = store.prepare_run(detection, collected)

    semantic_index = SemanticModelIndex(
        run_id=layout.run_id,
        languages=config.languages,
        modules=[],
        workflows=[],
        pages=[PageIndexItem(id="commands", kind="global", scope="global", target_ids=[])],
    )
    layout.semantic_index_file.write_text(semantic_index.model_dump_json(indent=2), encoding="utf-8")
    _write_receipt(
        layout,
        ChildSkillReceipt(
            job_id="page-write:commands:en",
            status="done",
            artifact_path=layout.rel_to_project(layout.page_artifacts_dir / "en" / "commands.md"),
            trace_path=layout.rel_to_project(layout.traces_dir / "commands-en.json"),
            attempt=1,
        ),
    )

    refreshed_state, _refreshed_index = store.refresh_state(layout, ["en"])
    page_job = next(job for job in refreshed_state.jobs if job.job_id == "page-write:commands:en")
    assert page_job.status == "stale"


def test_pipeline_falls_back_to_llm_scan_when_python_scan_fails(
    minimal_python_cli_dir: Path,
    monkeypatch,
):
    config = MakeWikiConfig.default(minimal_python_cli_dir)
    config.orchestration.resume = False
    config.scan.allow_llm_fallback_on_failure = True

    def fail_collect(self, project_dir, detection):
        raise RuntimeError("scanner import failure")

    monkeypatch.setattr(EvidenceCollector, "collect", fail_collect)

    ctx = Pipeline(config).run_until("prepare_run")

    assert not ctx.errors
    assert ctx.scan_fallback_required is True
    assert ctx.collected_evidence is not None
    assert ctx.collected_evidence.collection_mode == "llm-fallback"
    assert ctx.evidence_index is not None
    assert ctx.evidence_index.collection_mode == "llm-fallback"
    assert ctx.state is not None
    assert any(job.kind == "llm-scan" for job in ctx.state.jobs)


def test_pipeline_reports_detection_fallback_when_detector_fails(
    minimal_python_cli_dir: Path,
    monkeypatch,
):
    config = MakeWikiConfig.default(minimal_python_cli_dir)
    config.scan.allow_llm_fallback_on_failure = True
    config.orchestration.resume = False

    def fail_detect(self, project_dir):
        raise RuntimeError("detector unavailable")

    monkeypatch.setattr(ProjectDetector, "detect", fail_detect)
    monkeypatch.setattr(EvidenceCollector, "collect", lambda self, project_dir, detection: (_ for _ in ()).throw(RuntimeError("scan unavailable")))

    ctx = Pipeline(config).run_until("prepare_run")

    assert not ctx.errors
    assert ctx.detection is not None
    assert ctx.detection.project_name == minimal_python_cli_dir.name
    assert ctx.scan_fallback_required is True
    assert ctx.state is not None
    assert ctx.state.jobs[0].kind == "llm-scan"
