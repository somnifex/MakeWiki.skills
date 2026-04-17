"""Tests for CrossLanguageReviewer."""

from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer


def _doc(lang: str, base: str, content: str) -> GeneratedDocument:
    suffix = f".{lang}" if lang != "en" else ""
    parts = base.rsplit(".", 1)
    filename = f"{parts[0]}{suffix}.{parts[1]}" if suffix else base
    return GeneratedDocument(
        filename=filename,
        base_name=base,
        language_code=lang,
        content=content,
        word_count=len(content.split()),
    )


def test_identical_docs_no_deltas():
    """Two languages with identical commands and structure -> no critical deltas."""
    en = _doc("en", "README.md", "# App\n\n```bash\npip install foo\nfoo serve\n```\n")
    zh = _doc("zh-CN", "README.md", "# App\n\n```bash\npip install foo\nfoo serve\n```\n")

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en], "zh-CN": [zh]})

    assert result.passed
    # No command deltas
    cmd_deltas = [d for d in result.fact_deltas if d.fact_type == "command"]
    assert len(cmd_deltas) == 0


def test_missing_command_detected():
    """ZH-CN missing a command that EN has -> critical delta."""
    en = _doc("en", "README.md", "# App\n\n```bash\npip install foo\nfoo serve\n```\n")
    zh = _doc("zh-CN", "README.md", "# App\n\n```bash\npip install foo\n```\n")

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en], "zh-CN": [zh]})

    cmd_deltas = [d for d in result.fact_deltas if d.fact_type == "command"]
    assert len(cmd_deltas) >= 1
    missing_cmd = next(d for d in cmd_deltas if d.value == "foo serve")
    assert "zh-CN" in missing_cmd.missing_from
    assert missing_cmd.severity == "critical"


def test_missing_page_detected():
    """ZH-CN missing a whole page -> major delta."""
    en_readme = _doc("en", "README.md", "# App\n")
    en_install = _doc("en", "installation.md", "# Install\n")
    zh_readme = _doc("zh-CN", "README.md", "# App\n")

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en_readme, en_install], "zh-CN": [zh_readme]})

    page_deltas = [d for d in result.fact_deltas if d.fact_type == "page"]
    assert len(page_deltas) >= 1
    assert any(d.value == "installation.md" for d in page_deltas)


def test_config_key_inconsistency():
    """Different config keys between languages -> critical delta."""
    en = _doc("en", "config.md", "# Config\n\nSet `DB_HOST` and `DB_PORT`.\n")
    zh = _doc("zh-CN", "config.md", "# Config\n\nSet `DB_HOST`.\n")

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en], "zh-CN": [zh]})

    cfg_deltas = [d for d in result.fact_deltas if d.fact_type == "config_key"]
    assert any(d.value == "DB_PORT" for d in cfg_deltas)


def test_single_language_skips_review():
    """With only one language, review should pass trivially."""
    en = _doc("en", "README.md", "# App\n")
    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en]})
    assert result.passed
    assert result.consistency_score == 1.0


def test_revision_instructions_generated():
    """Review with issues should produce revision instructions."""
    en = _doc("en", "README.md", "# App\n\n```bash\nfoo serve\n```\n")
    zh = _doc("zh-CN", "README.md", "# App\n")

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en], "zh-CN": [zh]})
    instructions = reviewer.generate_revision_instructions(result)
    assert len(instructions) > 0
    assert any(i.target_language == "zh-CN" for i in instructions)
