"""Tests for DocExporter."""

from pathlib import Path

from makewiki_skills.renderer.exporter import DocExporter


def test_export_pdf_ready_html_and_epub(tmp_path: Path):
    wiki_dir = tmp_path / "makewiki"
    wiki_dir.mkdir()
    (wiki_dir / "README.md").write_text(
        "# Project Overview\n\nWelcome to the demo.\n", encoding="utf-8"
    )
    (wiki_dir / "getting-started.md").write_text(
        "# Getting Started\n\n```bash\nrun\n```\n", encoding="utf-8"
    )

    exporter = DocExporter(title="Test Project")
    html_file = exporter.export_pdf_ready_html(wiki_dir, lang="en")
    assert html_file.is_file()
    content = html_file.read_text(encoding="utf-8")
    assert "Print to PDF" in content
    assert "Project Overview" in content
    assert "Table of Contents" in content

    epub_file = exporter.export_epub(wiki_dir, lang="en")
    assert epub_file.is_file()
    assert epub_file.stat().st_size > 500


def test_export_non_english_default(tmp_path: Path):
    """default_language=ja: plain README.md is the ja chapter and README.en.md
    the en chapter — ``en`` is never hardcoded as the plain-``.md`` form.
    (The exporter exports its standard chapter set; README is one.)"""
    wiki_dir = tmp_path / "makewiki"
    wiki_dir.mkdir()
    (wiki_dir / "README.md").write_text("# プロジェクト\n\nja content.\n", encoding="utf-8")
    (wiki_dir / "README.en.md").write_text("# Project\n\nen content.\n", encoding="utf-8")

    exporter = DocExporter(title="Test Project")

    html_file = exporter.export_pdf_ready_html(wiki_dir, lang="ja", default_language="ja")
    assert html_file.name == "documentation.html"  # default language: no suffix
    content = html_file.read_text(encoding="utf-8")
    assert "プロジェクト" in content

    html_en = exporter.export_pdf_ready_html(wiki_dir, lang="en", default_language="ja")
    assert html_en.name == "documentation.en.html"
    en_content = html_en.read_text(encoding="utf-8")
    assert "Project" in en_content
    assert "プロジェクト" not in en_content  # plain .md must not leak into the en export

    epub_file = exporter.export_epub(wiki_dir, lang="ja", default_language="ja")
    assert epub_file.name == "documentation.epub"
    assert epub_file.stat().st_size > 500
