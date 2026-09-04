"""Tests for Confluence and Notion sync tools."""

from pathlib import Path

from makewiki_skills.sync.confluence import ConfluenceConverter, ConfluenceSyncTool
from makewiki_skills.sync.notion import NotionBlockConverter, NotionSyncTool


def test_confluence_converter():
    converter = ConfluenceConverter()
    md = "# Heading\n\n```python\nprint('hello')\n```\n\n> Note this.\n"
    xml = converter.to_storage_format(md)
    assert "<h1>Heading</h1>" in xml
    assert 'ac:name="code"' in xml
    assert "print('hello')" in xml
    assert 'ac:name="info"' in xml


def test_notion_converter():
    converter = NotionBlockConverter()
    md = "# Heading\n\n```bash\necho ok\n```\n\n- Bullet 1\n"
    blocks = converter.to_notion_blocks(md)
    block_types = [b["type"] for b in blocks]
    assert "heading_1" in block_types
    assert "code" in block_types
    assert "bulleted_list_item" in block_types


def test_sync_bundle_build(tmp_path: Path):
    wiki_dir = tmp_path / "makewiki"
    wiki_dir.mkdir()
    (wiki_dir / "README.md").write_text("# Overview\n\nDocumentation content.\n", encoding="utf-8")

    c_tool = ConfluenceSyncTool()
    c_dir = c_tool.build_sync_bundle(wiki_dir, space_key="TEST", lang="en")
    assert (c_dir / "manifest.json").is_file()
    assert (c_dir / "README.xml").is_file()

    n_tool = NotionSyncTool()
    n_dir = n_tool.build_sync_bundle(wiki_dir, parent_page_id="root-123", lang="en")
    assert (n_dir / "manifest.json").is_file()
    assert (n_dir / "README.json").is_file()


def test_sync_bundle_non_english_default(tmp_path: Path):
    """default_language=ja: guide.md (plain) is the ja page for lang=ja, and
    guide.en.md is the en page — ``en`` is never hardcoded as the default.
    Page ids strip the language suffix (long-standing contract); per-language
    bundle directories keep the languages apart."""
    wiki_dir = tmp_path / "makewiki"
    wiki_dir.mkdir()
    (wiki_dir / "guide.md").write_text("# ガイド\n\nja content.\n", encoding="utf-8")
    (wiki_dir / "guide.en.md").write_text("# Guide\n\nen content.\n", encoding="utf-8")

    c_tool = ConfluenceSyncTool()
    c_dir = c_tool.build_sync_bundle(wiki_dir, space_key="TEST", lang="ja", default_language="ja")
    assert (c_dir / "guide.xml").is_file()
    manifest = (c_dir / "manifest.json").read_text(encoding="utf-8")
    assert "ガイド" in manifest

    c_en = c_tool.build_sync_bundle(wiki_dir, space_key="TEST", lang="en", default_language="ja")
    assert (c_en / "guide.xml").is_file()
    c_en_manifest = (c_en / "manifest.json").read_text(encoding="utf-8")
    assert "Guide" in c_en_manifest
    assert "ガイド" not in c_en_manifest  # plain .md must not leak into the en bundle

    n_tool = NotionSyncTool()
    n_dir = n_tool.build_sync_bundle(wiki_dir, parent_page_id="root", lang="ja", default_language="ja")
    assert (n_dir / "guide.json").is_file()
    n_manifest = (n_dir / "manifest.json").read_text(encoding="utf-8")
    assert "ガイド" in n_manifest

    n_en = n_tool.build_sync_bundle(wiki_dir, parent_page_id="root", lang="en", default_language="ja")
    assert (n_en / "guide.json").is_file()
    n_en_manifest = (n_en / "manifest.json").read_text(encoding="utf-8")
    assert "Guide" in n_en_manifest
    assert "ガイド" not in n_en_manifest
