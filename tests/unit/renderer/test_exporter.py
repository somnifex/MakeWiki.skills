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
