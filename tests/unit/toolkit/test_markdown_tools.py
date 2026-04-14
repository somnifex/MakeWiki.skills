"""Tests for MarkdownTool."""

from makewiki_skills.toolkit.markdown_tools import MarkdownTool


def test_extract_headings():
    tool = MarkdownTool()
    content = "# Title\n\n## Section 1\n\n### Subsection\n\n## Section 2\n"
    headings = tool.extract_headings(content)
    assert len(headings) == 4
    assert headings[0].level == 1
    assert headings[0].text == "Title"
    assert headings[1].level == 2


def test_validate_headings_valid():
    tool = MarkdownTool()
    content = "# Title\n\n## Section\n\n### Sub\n"
    result = tool.validate_headings(content)
    assert result.success
    assert result.data["valid"]


def test_validate_headings_missing_h1():
    tool = MarkdownTool()
    content = "## Section\n\n### Sub\n"
    result = tool.validate_headings(content)
    assert result.success
    assert not result.data["valid"]
    issues = result.data["issues"]
    assert any(i["issue_type"] == "missing_h1" for i in issues)


def test_validate_headings_skipped_level():
    tool = MarkdownTool()
    content = "# Title\n\n### Skipped H2\n"
    result = tool.validate_headings(content)
    issues = result.data["issues"]
    assert any(i["issue_type"] == "heading_skip" for i in issues)


def test_extract_code_blocks():
    tool = MarkdownTool()
    content = "# Title\n\n```bash\npip install foo\n```\n\n```python\nprint('hi')\n```\n"
    blocks = tool.extract_code_blocks(content)
    assert len(blocks) == 2
    assert blocks[0].language == "bash"
    assert "pip install foo" in blocks[0].content
    assert blocks[1].language == "python"


def test_extract_facts_commands():
    tool = MarkdownTool()
    content = "# Readme\n\n```bash\npip install foo\nfoo serve\n```\n"
    facts = tool.extract_facts(content, "en", "README.md")
    assert "pip install foo" in facts.commands
    assert "foo serve" in facts.commands


def test_extract_facts_config_keys():
    tool = MarkdownTool()
    content = "Set `SERVER_HOST` and `DB_PORT` in your environment.\n"
    facts = tool.extract_facts(content)
    assert "SERVER_HOST" in facts.config_keys
    assert "DB_PORT" in facts.config_keys


def test_extract_facts_section_names():
    tool = MarkdownTool()
    content = "# My Project\n\n## Installation\n\n## Usage\n"
    facts = tool.extract_facts(content)
    assert "My Project" in facts.section_names
    assert "Installation" in facts.section_names
    assert "Usage" in facts.section_names


def test_check_empty():
    tool = MarkdownTool()
    assert tool.check_empty("# Title\n")
    assert tool.check_empty("")
    assert not tool.check_empty("# Title\n\nSome real content here that is meaningful.\n")


def test_validate_links_no_broken(tmp_path):
    (tmp_path / "other.md").write_text("# Other")
    tool = MarkdownTool()
    content = "# Test\n\n[Link](other.md)\n"
    target = tmp_path / "test.md"
    result = tool.validate_links(content, target)
    assert result.success
    assert result.data["valid"]


def test_validate_links_broken(tmp_path):
    tool = MarkdownTool()
    content = "# Test\n\n[Link](nonexistent.md)\n"
    target = tmp_path / "test.md"
    result = tool.validate_links(content, target)
    assert result.success
    assert not result.data["valid"]
    assert any(i["issue_type"] == "broken_link" for i in result.data["issues"])
