"""Tests for OutputManager, including delete_stale_files."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.renderer.output_manager import OutputManager


def _make_doc(filename: str, content: str = "# Test\n") -> GeneratedDocument:
    return GeneratedDocument(
        filename=filename,
        base_name=filename,
        language_code="en",
        content=content,
    )


def test_delete_stale_files_removes_old_docs(tmp_path: Path):
    """Stale .md files from a previous run should be deleted."""
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()

    # Simulate a previous run that produced old-page.md
    (output_dir / "old-page.md").write_text("# Old\n", encoding="utf-8")
    (output_dir / "README.md").write_text("# Old README\n", encoding="utf-8")

    manager = OutputManager(output_dir, overwrite=True, delete_stale_files=True)
    docs = {"en": [_make_doc("README.md", "# New README\n")]}
    manager.write_documents(docs)

    assert (output_dir / "README.md").exists()
    assert not (output_dir / "old-page.md").exists()


def test_delete_stale_files_removes_nested(tmp_path: Path):
    """Stale files in sub-directories should also be cleaned up."""
    output_dir = tmp_path / "makewiki"
    usage_dir = output_dir / "usage"
    usage_dir.mkdir(parents=True)

    (usage_dir / "old-module.md").write_text("# Old\n", encoding="utf-8")

    manager = OutputManager(output_dir, overwrite=True, delete_stale_files=True)
    docs = {"en": [_make_doc("usage/basic-usage.md", "# Usage\n")]}
    manager.write_documents(docs)

    assert (usage_dir / "basic-usage.md").exists()
    assert not (usage_dir / "old-module.md").exists()


def test_delete_stale_disabled_keeps_old_files(tmp_path: Path):
    """When delete_stale_files is False, old files should remain."""
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()

    (output_dir / "old-page.md").write_text("# Old\n", encoding="utf-8")

    manager = OutputManager(output_dir, overwrite=True, delete_stale_files=False)
    docs = {"en": [_make_doc("README.md", "# New\n")]}
    manager.write_documents(docs)

    assert (output_dir / "README.md").exists()
    assert (output_dir / "old-page.md").exists()


def test_delete_stale_preserves_non_md_files(tmp_path: Path):
    """Non-.md files (images, etc.) should not be touched."""
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()

    (output_dir / "logo.png").write_bytes(b"\x89PNG")
    (output_dir / "old-page.md").write_text("# Old\n", encoding="utf-8")

    manager = OutputManager(output_dir, overwrite=True, delete_stale_files=True)
    docs = {"en": [_make_doc("README.md")]}
    manager.write_documents(docs)

    assert (output_dir / "logo.png").exists()
    assert not (output_dir / "old-page.md").exists()
