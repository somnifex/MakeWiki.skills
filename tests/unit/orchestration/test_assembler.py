"""Tests for assembling page artifacts into final documents."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.orchestration.assembler import PageArtifactAssembler
from makewiki_skills.orchestration.models import PagePlan
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
    (layout.state_file).write_text(
        '{"run_id":"run-1","project_root":"%s","output_dir":"makewiki","max_attempts":2,"jobs":[]}\n'
        % str(tmp_path).replace("\\", "\\\\"),
        encoding="utf-8",
    )

    store = RunStore(config)
    assembler = PageArtifactAssembler(config)
    documents, warnings = assembler.assemble(layout, store)

    assert not warnings
    assert documents["en"][0].filename == "configuration.md"
    assert documents["zh-CN"][0].filename == "configuration.zh-CN.md"
    assert "[^low-1]" in documents["en"][0].content
    assert "Inferred by fallback scan from `src/app.py`." in documents["en"][0].content
