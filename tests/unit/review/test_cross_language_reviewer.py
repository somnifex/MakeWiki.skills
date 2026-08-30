"""Tests for CrossLanguageReviewer."""

from makewiki_skills.generator.language_generator import GeneratedDocument
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


def test_aligned_passages_pair_by_section_and_block_id_not_h2_index():
    """Aligned-passage extraction keys on stable section/block IDs, so sections
    reordered across languages still pair correctly (not by H2 position)."""
    en = _doc(
        "en",
        "guide.md",
        (
            "<!-- makewiki:section=usage -->\n"
            "# Usage\n"
            "[[id:run]]\n```bash\napp run\n```\n"
            "Run the app.\n"
            "\n"
            "<!-- makewiki:section=install -->\n"
            "# Install\n"
            "[[id:install.init]]\n```bash\napp init\n```\n"
        ),
    )
    # zh-CN reorders: install comes before usage; prose differs in meaning but
    # this is LLM-judged; alignment must still be by stable IDs.
    zh = _doc(
        "zh-CN",
        "guide.md",
        (
            "<!-- makewiki:section=install -->\n"
            "# 安装\n"
            "[[id:install.init]]\n```bash\napp init\n```\n"
            "\n"
            "<!-- makewiki:section=usage -->\n"
            "# 用法\n"
            "[[id:run]]\n```bash\napp run\n```\n"
        ),
    )

    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents({"en": [en], "zh-CN": [zh]})

    prose = [p for p in passages if p.block_id is None]
    code = [p for p in passages if p.block_id is not None]

    # Prose passages are keyed by stable section id, not H2 index/text.
    prose_by_section = {p.section_id: p for p in prose}
    assert set(prose_by_section) == {"usage", "install"}
    assert sorted(prose_by_section["usage"].languages) == ["en", "zh-CN"]
    assert sorted(prose_by_section["install"].languages) == ["en", "zh-CN"]

    # Code passages are keyed by (section_id, block_id) and pair across langs.
    code_keys = {(p.section_id, p.block_id) for p in code}
    assert ("usage", "run") in code_keys
    assert ("install", "install.init") in code_keys
    run = next(p for p in code if (p.section_id, p.block_id) == ("usage", "run"))
    assert sorted(run.languages) == ["en", "zh-CN"]
    assert "app run" in run.texts["en"] and "app run" in run.texts["zh-CN"]

    # The prose seen by the LLM excludes the code fences.
    assert "```" not in prose_by_section["usage"].texts["en"]


def test_aligned_passages_never_judge_meaning():
    """align_documents only aligns; differing prose is preserved per language
    (L4b meaning judgment is left to the LLM, never decided here)."""
    en = _doc("en", "g.md", "<!-- makewiki:section=s -->\n# S\nEnglish prose.\n")
    zh = _doc("zh-CN", "g.md", "<!-- makewiki:section=s -->\n# S\n\n中文正文。\n")

    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents({"en": [en], "zh-CN": [zh]})

    prose = next(p for p in passages if p.block_id is None and p.section_id == "s")
    # Both languages' text are surfaced verbatim; no equality verdict is made.
    assert "English prose." in prose.texts["en"]
    assert "中文正文" in prose.texts["zh-CN"]
    assert prose.languages == ["en", "zh-CN"]

