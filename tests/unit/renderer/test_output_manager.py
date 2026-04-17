"""Tests for OutputManager, including delete_stale_files."""

from pathlib import Path

from makewiki_skills.documents import GeneratedDocument
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
    modules_dir = output_dir / "modules"
    modules_dir.mkdir(parents=True)

    (modules_dir / "old-module.md").write_text("# Old\n", encoding="utf-8")

    manager = OutputManager(output_dir, overwrite=True, delete_stale_files=True)
    docs = {"en": [_make_doc("modules/core.md", "# Core\n")]}
    manager.write_documents(docs)

    assert (modules_dir / "core.md").exists()
    assert not (modules_dir / "old-module.md").exists()


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


def test_output_manager_uses_readme_as_entry_page(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "index.md").write_text("# Old Index\n", encoding="utf-8")

    manager = OutputManager(output_dir, overwrite=True, delete_stale_files=False)
    docs = {
        "en": [
            _make_doc("commands.md", "# Commands\n"),
            _make_doc("README.md", "# Project\n"),
        ]
    }
    written = manager.write_documents(docs, default_language="en")

    assert written[0].name == "README.md"
    assert not (output_dir / "index.md").exists()
    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    assert "## Documentation Index" in readme
    assert "commands.md" in readme
