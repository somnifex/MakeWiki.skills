"""Helpers for seeding orchestration artifacts in integration tests."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.orchestration.models import (
    ChildSkillReceipt,
    ModuleIndexItem,
    PageIndexItem,
    PagePlan,
    SemanticModelIndex,
    WorkflowIndexItem,
)
from makewiki_skills.pipeline.pipeline import Pipeline


def seed_run_artifacts(
    project_dir: Path,
    config: MakeWikiConfig,
    *,
    project_name: str,
    command: str,
    entry_path: str,
    config_key: str = "APP_ENV",
    include_integrations: bool = True,
) -> str:
    ctx = Pipeline(config).run_until("prepare_run")
    assert ctx.run_layout is not None
    assert ctx.state is not None
    layout = ctx.run_layout

    for job in ctx.state.jobs:
        if job.kind != "surface-card" or job.artifact_path is None or job.source_ref is None:
            continue
        artifact_file = project_dir / job.artifact_path
        artifact_file.parent.mkdir(parents=True, exist_ok=True)
        artifact_file.write_text('{"source_ref":"%s"}\n' % job.source_ref, encoding="utf-8")
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

    modules = [ModuleIndexItem(id="core", name="Core Tasks")]
    workflows = [WorkflowIndexItem(id="hello-world", name="Hello World", module_ids=["core"])]
    pages = [
        PageIndexItem(id="readme", kind="global", scope="global", target_ids=[]),
        PageIndexItem(id="getting-started", kind="global", scope="global", target_ids=[]),
        PageIndexItem(id="installation", kind="global", scope="global", target_ids=[]),
        PageIndexItem(id="configuration", kind="global", scope="global", target_ids=[]),
        PageIndexItem(id="commands", kind="global", scope="global", target_ids=[]),
        PageIndexItem(id="modules-overview", kind="overview", scope="module", target_ids=["core"]),
        PageIndexItem(id="module-core", kind="module", scope="module", target_ids=["core"]),
        PageIndexItem(
            id="workflows-overview",
            kind="overview",
            scope="workflow",
            target_ids=["hello-world"],
        ),
        PageIndexItem(
            id="workflow-hello-world",
            kind="workflow",
            scope="workflow",
            target_ids=["hello-world"],
        ),
        PageIndexItem(id="faq", kind="global", scope="global", target_ids=[]),
        PageIndexItem(id="troubleshooting", kind="global", scope="global", target_ids=[]),
    ]
    if include_integrations:
        pages.append(
            PageIndexItem(
                id="integrations-overview",
                kind="integration",
                scope="integration",
                target_ids=[],
            )
        )

    semantic_index = SemanticModelIndex(
        run_id=layout.run_id,
        languages=config.languages,
        modules=modules,
        workflows=workflows,
        pages=pages,
    )
    layout.project_brief_file.write_text(
        '{"name":"%s","purpose":"Example project brief"}\n' % project_name,
        encoding="utf-8",
    )
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

    for module in modules:
        artifact_file = layout.module_briefs_dir / f"{module.id}.json"
        artifact_file.write_text('{"id":"%s","name":"%s"}\n' % (module.id, module.name), encoding="utf-8")
        _write_receipt(
            layout,
            ChildSkillReceipt(
                job_id=f"module-brief:{module.id}",
                status="done",
                artifact_path=layout.rel_to_project(artifact_file),
                trace_path=layout.rel_to_project(layout.traces_dir / f"module-{module.id}.json"),
                attempt=1,
            ),
        )

    for workflow in workflows:
        artifact_file = layout.workflow_briefs_dir / f"{workflow.id}.json"
        artifact_file.write_text(
            '{"id":"%s","name":"%s"}\n' % (workflow.id, workflow.name),
            encoding="utf-8",
        )
        _write_receipt(
            layout,
            ChildSkillReceipt(
                job_id=f"workflow-brief:{workflow.id}",
                status="done",
                artifact_path=layout.rel_to_project(artifact_file),
                trace_path=layout.rel_to_project(layout.traces_dir / f"workflow-{workflow.id}.json"),
                attempt=1,
            ),
        )

    output_map = {
        "readme": "README.md",
        "getting-started": "getting-started.md",
        "installation": "installation.md",
        "configuration": "configuration.md",
        "commands": "commands.md",
        "modules-overview": "modules/overview.md",
        "module-core": "modules/core.md",
        "workflows-overview": "workflows/overview.md",
        "workflow-hello-world": "workflows/hello-world.md",
        "faq": "faq.md",
        "troubleshooting": "troubleshooting.md",
        "integrations-overview": "integrations/overview.md",
    }

    for page in pages:
        plan = PagePlan(
            page_id=page.id,
            output_path=output_map[page.id],
            kind=page.kind,
            scope=page.scope,
            target_ids=page.target_ids,
        )
        artifact_file = layout.page_plans_dir / f"{page.id}.json"
        artifact_file.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        _write_receipt(
            layout,
            ChildSkillReceipt(
                job_id=f"page-plan:{page.id}",
                status="done",
                artifact_path=layout.rel_to_project(artifact_file),
                trace_path=layout.rel_to_project(layout.traces_dir / f"page-plan-{page.id}.json"),
                attempt=1,
            ),
        )
        for language in config.languages:
            page_file = layout.page_artifacts_dir / language / f"{page.id}.md"
            page_file.parent.mkdir(parents=True, exist_ok=True)
            page_file.write_text(
                _page_content(
                    page_id=page.id,
                    project_name=project_name,
                    command=command,
                    entry_path=entry_path,
                    config_key=config_key,
                    language=language,
                ),
                encoding="utf-8",
            )
            _write_receipt(
                layout,
                ChildSkillReceipt(
                    job_id=f"page-write:{page.id}:{language}",
                    status="done",
                    artifact_path=layout.rel_to_project(page_file),
                    trace_path=layout.rel_to_project(
                        layout.traces_dir / f"page-write-{page.id}-{language}.json"
                    ),
                    attempt=1,
                ),
            )

    return layout.run_id


def _page_content(
    *,
    page_id: str,
    project_name: str,
    command: str,
    entry_path: str,
    config_key: str,
    language: str,
) -> str:
    zh = language == "zh-CN"
    title_map = {
        "readme": "README" if not zh else "README",
        "getting-started": "Getting Started" if not zh else "快速开始",
        "installation": "Installation" if not zh else "安装",
        "configuration": "Configuration" if not zh else "配置",
        "commands": "Commands" if not zh else "命令",
        "modules-overview": "Module Overview" if not zh else "模块总览",
        "module-core": "Core Tasks" if not zh else "核心任务",
        "workflows-overview": "Workflow Overview" if not zh else "工作流总览",
        "workflow-hello-world": "Hello World Workflow" if not zh else "Hello World 工作流",
        "faq": "FAQ" if not zh else "FAQ",
        "troubleshooting": "Troubleshooting" if not zh else "排障",
        "integrations-overview": "Integrations" if not zh else "集成",
    }
    title = title_map[page_id]
    if page_id == "readme":
        return (
            f"# {project_name}\n\n"
            f"{project_name} exposes a small user-facing surface for command-line work.\n\n"
            f"## Quick Start\n\n```bash\n{command}\n```\n"
        )
    if page_id == "getting-started":
        return f"# {title}\n\n```bash\n{command}\n```\n"
    if page_id == "installation":
        return "# Installation\n\n```bash\npip install -e .\n```\n"
    if page_id == "configuration":
        body = "Use" if not zh else "使用"
        return (
            f"# {title}\n\n"
            f"| Key | Description |\n|---|---|\n| `{config_key}` | {body} runtime settings{{{{LOW_CONFIDENCE:{entry_path.lstrip('./')}}}}} |\n"
        )
    if page_id == "commands":
        return f"# {title}\n\n```bash\n{command}\n```\n"
    if page_id == "modules-overview":
        return f"# {title}\n\n- [Core](core.md)\n"
    if page_id == "module-core":
        return (
            f"# {title}\n\n"
            f"See `{entry_path}` for the entrypoint.\n\n"
            f"```bash\n{command}\n```\n"
        )
    if page_id == "workflows-overview":
        return f"# {title}\n\n- [Hello World](hello-world.md)\n"
    if page_id == "workflow-hello-world":
        return f"# {title}\n\n```bash\n{command}\n```\n"
    if page_id == "faq":
        return f"# {title}\n\n## Q1\n\n`{command}` is the primary example.\n"
    if page_id == "troubleshooting":
        return f"# {title}\n\nIf the command fails, verify `{entry_path}` exists.\n"
    return f"# {title}\n\nThis page describes an external integration surface.\n"


def _write_receipt(layout, receipt: ChildSkillReceipt) -> None:
    receipt_path = layout.receipts_dir / f"{receipt.job_id.replace(':', '__')}.{receipt.attempt}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
