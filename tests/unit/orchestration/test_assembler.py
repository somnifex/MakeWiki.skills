"""Tests for assembling page artifacts into final documents."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.orchestration.assembler import PageArtifactAssembler
from makewiki_skills.orchestration.models import PagePlan, RunJob, RunState
from makewiki_skills.orchestration.store import RunLayout, RunStore


def test_assembler_applies_language_suffix_and_confidence_footnotes(tmp_path: Path):
    config = MakeWikiConfig.default(tmp_path)
    config.languages = ["en", "zh-CN"]

    layout = RunLayout.create(tmp_path, config.orchestration.state_dir, "run-1")
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
        "# 配置\n\n使用 `SERVER_PORT` 控制端口{{LOW_CONFIDENCE:src/app.py}}。\n",
        encoding="utf-8",
    )
    state = RunState(
        run_id="run-1",
        project_root=str(tmp_path),
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

    store = RunStore(config)
    assembler = PageArtifactAssembler(config)
    documents, warnings = assembler.assemble(layout, store)

    assert not warnings
    assert documents["en"][0].filename == "configuration.md"
    assert documents["zh-CN"][0].filename == "configuration.zh-CN.md"
    assert "[^low-1]" in documents["en"][0].content
    assert "Inferred by fallback scan from `src/app.py`." in documents["en"][0].content


def test_assembler_skips_non_done_page_jobs(tmp_path: Path):
    config = MakeWikiConfig.default(tmp_path)
    config.languages = ["en"]

    layout = RunLayout.create(tmp_path, config.orchestration.state_dir, "run-2")
    layout.ensure_dirs()
    (layout.page_plans_dir / "readme.json").write_text(
        PagePlan(
            page_id="readme",
            output_path="README.md",
            kind="global",
            scope="global",
            target_ids=[],
        ).model_dump_json(indent=2),
        encoding="utf-8",
    )
    (layout.page_artifacts_dir / "en").mkdir(parents=True, exist_ok=True)
    (layout.page_artifacts_dir / "en" / "readme.md").write_text("# Stale\n", encoding="utf-8")
    state = RunState(
        run_id="run-2",
        project_root=str(tmp_path),
        output_dir="makewiki",
        languages=["en"],
        default_language="en",
        max_attempts=2,
        jobs=[
            RunJob(
                job_id="page-plan:readme",
                kind="page-plan",
                page_id="readme",
                status="done",
            ),
            RunJob(
                job_id="page-write:readme:en",
                kind="page-write",
                page_id="readme",
                language_code="en",
                status="failed",
            ),
        ],
    )
    layout.state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    documents, warnings = PageArtifactAssembler(config).assemble(layout, RunStore(config))

    assert documents["en"] == []
    assert any("page-write job is not done" in warning for warning in warnings)
