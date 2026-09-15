"""Unit tests for the mechanical rendered-output audit (``verify-html``).

The audit answers for the GENERATED artifacts: it re-pairs each rendered body
with the Markdown that produced it, segment by segment (preamble + H2), and
runs mechanical checks per pair. These tests pin both directions: a clean wiki
passes with zero findings, and each proven defect class (marker leak, heading
drift, dropped prose/cells/sections) is detected at its exact location.
"""

from __future__ import annotations

import json

from makewiki_skills.verification.render_audit import audit_markdown_pair, run_render_audit

# --- pure pair checks (no filesystem) -----------------------------------------


def test_clean_pair_produces_no_findings() -> None:
    source = "# Doc\n\n## One\n\nalpha beta gamma\n"
    rendered = "<h1 id=\"doc\">Doc</h1>\n<h2 id=\"one\">One</h2>\n<p>alpha beta gamma</p>\n"
    findings, segments = audit_markdown_pair(
        language="en", document_id="doc", source_md=source, rendered_html=rendered
    )
    assert findings == []
    assert segments == 2  # preamble + one section


def test_dropped_section_is_a_blocking_finding() -> None:
    source = "# Doc\n\n## One\n\nalpha beta gamma\n\n## Two\n\ndelta epsilon zeta\n"
    rendered = "<h1 id=\"doc\">Doc</h1>\n<h2 id=\"one\">One</h2>\n<p>alpha beta gamma</p>\n"
    findings, segments = audit_markdown_pair(
        language="en", document_id="doc", source_md=source, rendered_html=rendered
    )
    parity = [f for f in findings if f.check == "heading_parity"]
    assert segments == 3  # preamble + two sections on the source side
    assert any(f.severity == "major" for f in findings)


def test_marker_leak_in_prose_is_critical() -> None:
    findings, _ = audit_markdown_pair(
        language="en",
        document_id="doc",
        source_md="## H\n\nsee the note\n",
        rendered_html="<h2 id=\"h\">H</h2>\n<p>see the [[id:leaked]] note</p>",
    )
    leaks = [f for f in findings if f.check == "marker_leak"]
    assert leaks and leaks[0].severity == "critical"


def test_escaped_comment_leak_is_critical() -> None:
    # The duplicated-renderer-era symptom: an html comment escaped into text.
    findings, _ = audit_markdown_pair(
        language="en",
        document_id="doc",
        source_md="> [!NOTE]\n> heed this\n",
        rendered_html="<blockquote><p>[!NOTE] heed this</p></blockquote>",
    )
    assert any(f.check == "marker_leak" and f.severity == "critical" for f in findings)


def test_table_integrity_catches_dropped_cells() -> None:
    source = "## T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    rendered = "<h2 id=\"t\">T</h2>\n<table><thead><tr><th>a</th></tr></thead>"
    findings, _ = audit_markdown_pair(
        language="en", document_id="d", source_md=source, rendered_html=rendered
    )
    assert any(f.check == "table_integrity" for f in findings)


def test_fenced_block_count_mismatch_is_blocking() -> None:
    source = "## S\n\n```bash\nmake build\n```\n"
    rendered = "<h2 id=\"s\">S</h2>\n<p>nothing here</p>\n"
    findings, _ = audit_markdown_pair(
        language="en", document_id="d", source_md=source, rendered_html=rendered
    )
    assert any(f.check == "code_block_parity" for f in findings)


def test_callout_not_transformed_leaks_visible_marker() -> None:
    findings, _ = audit_markdown_pair(
        language="en",
        document_id="doc",
        source_md="> [!NOTE]\n> heed this\n",
        rendered_html="<blockquote><p>[!NOTE] heed this</p></blockquote>",
    )
    assert any(f.check == "marker_leak" for f in findings)


def test_dropped_section_is_blocking() -> None:
    source = "# Doc\n\n## One\n\nalpha beta gamma\n\n## Two\n\ndelta epsilon zeta\n"
    rendered = "<h1 id=\"doc\">Doc</h1>\n<h2 id=\"one\">One</h2>\n<p>alpha beta gamma</p>\n"
    findings, _ = audit_markdown_pair(
        language="en", document_id="doc", source_md=source, rendered_html=rendered
    )
    assert any(f.check == "heading_parity" for f in findings)


# --- artifact-level: real compile + audit round trip ---------------------------


def _plan() -> "SitePresentationPlan":
    from makewiki_skills.model.site_presentation import (
        SiteNavItem,
        SitePresentationPlan,
        SiteVisualPreferences,
    )

    return SitePresentationPlan(
        project_title="T",
        project_description="d",
        navigation=[
            SiteNavItem(document_id="README", route="/", title="Home", nav_group="G", ordering=10),
            SiteNavItem(
                document_id="getting-started",
                route="/gs",
                title="Quick Start",
                nav_group="G",
                ordering=20,
            ),
        ],
        languages=["en", "zh-CN"],
        default_language="en",
        visual=SiteVisualPreferences(theme="auto", include_search=True),
    )


def _build_all(tmp_path: Path) -> Path:
    from makewiki_skills.renderer.exporter import DocExporter
    from makewiki_skills.renderer.site_compiler import SiteCompiler

    makewiki = tmp_path / "makewiki"
    makewiki.mkdir(exist_ok=True)
    plan = _plan()
    (makewiki / "README.md").write_text(
        "# Sample Project\n\n<!-- makewiki:section=intro -->\n\n## Intro\n\n"
        "Welcome to the demo project.\n\nSee [guide](getting-started.md).\n",
        encoding="utf-8",
    )
    (makewiki / "README.zh-CN.md").write_text(
        "# 示例项目\n\n<!-- makewiki:section=intro -->\n\n## 简介\n\n欢迎使用示例项目。\n",
        encoding="utf-8",
    )
    (makewiki / "getting-started.md").write_text(
        "# Quick Start\n\nRun `npm install` twice.\n", encoding="utf-8"
    )
    (makewiki / "site_presentation.json").write_text(
        json.dumps(plan.model_dump(), ensure_ascii=False), encoding="utf-8"
    )
    SiteCompiler(plan=plan).compile(makewiki)
    DocExporter(title="T").export_pdf_ready_html(makewiki, lang="en")
    return makewiki


def test_rendered_output_audit_passes_real_artifacts(tmp_path: Path) -> None:
    makewiki = _build_all(tmp_path)
    result = run_render_audit(makewiki, target="all")
    assert result.verdict == "passed", [f.model_dump() for f in result.blocking]
    assert len(result.artifacts) >= 1
    assert result.documents_audited >= 2
    assert result.segments_audited >= 2


def test_marker_stripping_regression_is_caught(tmp_path: Path) -> None:
    import unittest.mock as mock

    import makewiki_skills.renderer.markdown_render as mr
    from makewiki_skills.renderer.site_compiler import SiteCompiler

    makewiki = _build_all(tmp_path)
    with mock.patch.object(mr, "strip_build_metadata", lambda md: md):
        SiteCompiler(plan=_plan()).compile(makewiki, makewiki / "site")
    leak_result = run_render_audit(makewiki, target="site")
    assert leak_result.verdict == "failed"
    assert any(f.check == "marker_leak" for f in leak_result.blocking)
    assert "README" in {f.document_id for f in leak_result.blocking}
