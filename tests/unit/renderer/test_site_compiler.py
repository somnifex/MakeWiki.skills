"""Unit tests for the plan-driven SiteCompiler.

The SiteCompiler is a PURE MECHANICAL renderer: it consumes an LLM-authored
SitePresentationPlan that declares the site IA (navigation groups, ordering,
routes, hierarchy, localized titles) and renders exactly that plan. These tests
verify the compiler renders the plan's IA mechanically and refuses to invent one
when no plan is provided (requirement: Python never classifies pages from
filenames).
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.model.site_presentation import (
    SiteNavItem,
    SitePresentationPlan,
    SiteVisualPreferences,
)
from makewiki_skills.renderer.site_compiler import (
    SiteCompiler,
    SitePlanRequiredError,
)


def _plan() -> SitePresentationPlan:
    return SitePresentationPlan(
        project_title="Test Wiki",
        project_description="A sample project.",
        navigation=[
            SiteNavItem(
                document_id="README",
                route="/",
                title="Home",
                titles={"zh-CN": "首页"},
                nav_group="Overview",
                ordering=10,
            ),
            SiteNavItem(
                document_id="getting-started",
                route="/getting-started",
                title="Quick Start",
                titles={"zh-CN": "快速起步"},
                nav_group="Getting Started",
                ordering=20,
            ),
            SiteNavItem(
                document_id="usage/overview",
                route="/usage",
                title="Usage",
                nav_group="Usage",
                ordering=30,
                children=[
                    SiteNavItem(
                        document_id="usage/deploy",
                        route="/deploy",
                        title="Deploy",
                        nav_group="Usage",
                        ordering=10,
                    )
                ],
            ),
        ],
        languages=["en", "zh-CN"],
        default_language="en",
        visual=SiteVisualPreferences(theme="dark", include_search=True),
    )


def test_site_compiler_compiles_markdown_to_spa(tmp_path: Path) -> None:
    makewiki_dir = tmp_path / "makewiki"
    makewiki_dir.mkdir()

    (makewiki_dir / "README.md").write_text(
        "# Sample Project\n\nWelcome to sample project.", encoding="utf-8"
    )
    (makewiki_dir / "README.zh-CN.md").write_text(
        "# 示例项目\n\n欢迎使用示例项目。", encoding="utf-8"
    )
    (makewiki_dir / "getting-started.md").write_text(
        "# Quick Start\n\nRun `npm install`.", encoding="utf-8"
    )
    (makewiki_dir / "getting-started.zh-CN.md").write_text(
        "# 快速起步\n\n运行 `npm install`。", encoding="utf-8"
    )
    usage_dir = makewiki_dir / "usage"
    usage_dir.mkdir()
    (usage_dir / "overview.md").write_text(
        "# Usage Overview\n\nModule summary.", encoding="utf-8"
    )
    (usage_dir / "deploy.md").write_text("# Deploy\n\nDeploy steps.", encoding="utf-8")
    (usage_dir / "deploy.zh-CN.md").write_text("# 部署\n\n部署步骤。", encoding="utf-8")

    compiler = SiteCompiler(plan=_plan())
    written = compiler.compile(makewiki_dir)

    assert len(written) == 1
    index_html = Path(written[0])
    assert index_html.is_file()

    content = index_html.read_text(encoding="utf-8")
    # Localized project + doc titles rendered from the plan/doc content.
    assert "Sample Project" in content
    assert "示例项目" in content
    # Plan-driven visual direction (theme) is embedded for the JS to apply.
    assert '"theme": "dark"' in content
    # Plan-driven navigation: groups and routes come from the plan, not filenames.
    assert "siteNav" in content
    assert "siteConfig" in content
    assert "docsContent" in content
    assert "Getting Started" in content  # nav group declared by the LLM plan
    assert "navigateTo" in content
    assert "resolveInternalSlug" in content
    assert "wiki-link" in content


def test_site_compiler_renders_plan_navigation_verbatim(tmp_path: Path) -> None:
    """Sidebar nav (groups, ordering, hierarchy, routes) comes from the plan."""
    makewiki_dir = tmp_path / "makewiki"
    makewiki_dir.mkdir()
    (makewiki_dir / "README.md").write_text("# Home\n\nwelcome\n", encoding="utf-8")
    gs = makewiki_dir / "getting-started.md"
    gs.write_text("# Quick Start\n\nStep 1\n", encoding="utf-8")
    usage = makewiki_dir / "usage"
    usage.mkdir()
    (usage / "overview.md").write_text("# Usage Overview\n\nx\n", encoding="utf-8")
    (usage / "deploy.md").write_text("# Deploy\n\ny\n", encoding="utf-8")

    compiler = SiteCompiler(plan=_plan())
    written = compiler.compile(makewiki_dir)
    content = Path(written[0]).read_text(encoding="utf-8")

    # The plan's nav is serialized into siteNav verbatim: groups, order, routes,
    # hierarchy (children), localized titles.
    assert '"route": "/"' in content
    assert '"route": "/getting-started"' in content
    assert '"route": "/deploy"' in content
    assert '"group": "Getting Started"' in content
    assert '"children"' in content
    assert '"titles"' in content


def test_site_compiler_requires_plan_and_never_fabricates_ia(tmp_path: Path) -> None:
    makewiki_dir = tmp_path / "makewiki"
    makewiki_dir.mkdir()
    # A "getting-started" / "faq" file MUST NOT be auto-classified into nav
    # groups when no plan is present.
    (makewiki_dir / "README.md").write_text("# Home\n", encoding="utf-8")
    (makewiki_dir / "getting-started.md").write_text("# Quick Start\n", encoding="utf-8")
    (makewiki_dir / "faq.md").write_text("# FAQ\n", encoding="utf-8")

    try:
        SiteCompiler().compile(makewiki_dir)
    except SitePlanRequiredError:
        pass
    else:
        raise AssertionError(
            "SiteCompiler must refuse to build without a SitePresentationPlan — "
            "it must never fabricate an Information Architecture from filenames."
        )


def test_site_compiler_links_in_index_doc(tmp_path: Path) -> None:
    makewiki_dir = tmp_path / "makewiki"
    makewiki_dir.mkdir()

    (makewiki_dir / "index.md").write_text(
        "# Index\n\n- [README.md](README.md)\n- [Quick Start](getting-started.md)\n",
        encoding="utf-8",
    )
    (makewiki_dir / "README.md").write_text(
        "# Readme\n\n[Go to Config](configuration.md)\n", encoding="utf-8"
    )
    (makewiki_dir / "getting-started.md").write_text(
        "# Getting Started\n\nStep 1", encoding="utf-8"
    )
    (makewiki_dir / "configuration.md").write_text("# Config\n\nKey: Value", encoding="utf-8")

    plan = SitePresentationPlan(
        project_title="Links Wiki",
        navigation=[
            SiteNavItem(
                document_id="index", route="/", title="Index", nav_group="Overview", ordering=10
            ),
            SiteNavItem(
                document_id="README",
                route="/readme",
                title="Readme",
                nav_group="Overview",
                ordering=20,
            ),
            SiteNavItem(
                document_id="getting-started",
                route="/getting-started",
                title="Getting Started",
                nav_group="Getting Started",
                ordering=30,
            ),
            SiteNavItem(
                document_id="configuration",
                route="/config",
                title="Config",
                nav_group="Reference",
                ordering=40,
            ),
        ],
        languages=["en"],
        default_language="en",
    )

    compiler = SiteCompiler(plan=plan)
    written = compiler.compile(makewiki_dir)
    assert len(written) == 1
    content = Path(written[0]).read_text(encoding="utf-8")
    assert "docsContent" in content
    assert "siteNav" in content
    assert "navigateTo" in content
