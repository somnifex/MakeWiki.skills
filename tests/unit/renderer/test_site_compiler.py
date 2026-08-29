"""Unit tests for SiteCompiler."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.renderer.site_compiler import SiteCompiler


def test_site_compiler_compiles_markdown_to_spa(tmp_path: Path) -> None:
    makewiki_dir = tmp_path / "makewiki"
    makewiki_dir.mkdir()

    # Create sample docs in English and Chinese
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
    (usage_dir / "overview.md").write_text("# Usage Overview\n\nModule summary.", encoding="utf-8")

    compiler = SiteCompiler(title="Test Wiki", theme="dark")
    written = compiler.compile(makewiki_dir)

    assert len(written) == 1
    index_html = Path(written[0])
    assert index_html.is_file()

    content = index_html.read_text(encoding="utf-8")
    assert "Sample Project" in content
    assert "示例项目" in content
    assert 'data-theme="dark"' in content
    assert "MakeWiki" in content
    assert "searchInput" in content
    assert "langSelect" in content
    assert "navigateTo" in content
    assert "resolveInternalSlug" in content
    assert "wiki-link" in content


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

    compiler = SiteCompiler()
    written = compiler.compile(makewiki_dir)
    assert len(written) == 1
    content = Path(written[0]).read_text(encoding="utf-8")
    assert "docsData" in content
    assert "navigateTo" in content
