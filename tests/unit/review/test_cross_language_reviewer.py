"""Tests for CrossLanguageReviewer."""

from makewiki_skills.model.document_artifact import GeneratedDocument
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
    # The passage is document-scoped: document_id is the doc's base_name.
    assert prose_by_section["usage"].document_id == "guide.md"
    assert prose_by_section["install"].document_id == "guide.md"

    # Code passages are keyed by (section_id, block_id) per document and pair
    # across langs; the document is part of the stable identity namespace.
    code_keys = {(p.document_id, p.section_id, p.block_id) for p in code}
    assert ("guide.md", "usage", "run") in code_keys
    assert ("guide.md", "install", "install.init") in code_keys
    run = next(p for p in code if (p.section_id, p.block_id) == ("usage", "run"))
    assert run.document_id == "guide.md"
    assert sorted(run.languages) == ["en", "zh-CN"]
    assert "app run" in run.texts["en"] and "app run" in run.texts["zh-CN"]
    # The stable review_item_id for code passages carries the document + block.
    assert run.review_item_id == "L4b:guide.md:usage:block:run"

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
    # The passage is scoped to its document and carries a stable review id.
    assert prose.document_id == "g.md"
    assert prose.review_item_id == "L4b:g.md:s"


# ---------------------------------------------------------------------------
# New §14 tests: multilingual stable section identity
# ---------------------------------------------------------------------------


def _reordered_fixture() -> dict[str, list]:
    """EN order install/config/usage; ZH-CN order install/usage/config with
    DIFFERENT H2 wording. Same stable section IDs, different section order."""
    en = _doc(
        "en",
        "guide.md",
        (
            "<!-- makewiki:section=install -->\n"
            "## Install the app\n"
            "EN install prose.\n"
            "\n"
            "<!-- makewiki:section=config -->\n"
            "## Configure the app\n"
            "EN config prose.\n"
            "\n"
            "<!-- makewiki:section=usage -->\n"
            "## Use the app\n"
            "EN usage prose.\n"
        ),
    )
    zh = _doc(
        "zh-CN",
        "guide.md",
        (
            "<!-- makewiki:section=install -->\n"
            "## 安装应用\n"
            "ZH install prose.\n"
            "\n"
            "<!-- makewiki:section=usage -->\n"
            "## 使用应用\n"
            "ZH usage prose.\n"
            "\n"
            "<!-- makewiki:section=config -->\n"
            "## 配置应用\n"
            "ZH config prose.\n"
        ),
    )
    return {"en": [en], "zh-CN": [zh]}


def test_semantic_review_pairs_reordered_sections_by_id():
    """Sections reordered AND reworded across languages still pair BY ID — the
    install/config/usage passages never realign by heading text or position."""
    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents(_reordered_fixture())

    prose = {p.section_id: p for p in passages if p.block_id is None}
    assert set(prose) == {"install", "config", "usage"}

    for section_id in ("install", "config", "usage"):
        p = prose[section_id]
        assert p.document_id == "guide.md"
        assert p.languages == ["en", "zh-CN"]
        assert p.texts["en"] == f"EN {section_id} prose."
        assert p.texts["zh-CN"] == f"ZH {section_id} prose."


def test_semantic_review_never_pairs_by_position():
    """The same reorder fixture must never cross-contaminate: en['config'] never
    pairs with zh-CN['usage'] merely because they share a heading position."""
    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents(_reordered_fixture())

    prose = {p.section_id: p for p in passages if p.block_id is None}
    # config passage holds EN config + ZH config, never ZH usage (cross-section).
    assert prose["config"].texts == {
        "en": "EN config prose.",
        "zh-CN": "ZH config prose.",
    }
    assert prose["usage"].texts == {
        "en": "EN usage prose.",
        "zh-CN": "ZH usage prose.",
    }
    assert prose["install"].texts == {
        "en": "EN install prose.",
        "zh-CN": "ZH install prose.",
    }
    # No passage mixes sections across languages.
    for p in prose.values():
        assert set(p.texts.values()) == {
            f"EN {p.section_id} prose.",
            f"ZH {p.section_id} prose.",
        }


def test_missing_section_is_not_replaced_by_next_section():
    """EN has sections a and b; ZH-CN has only a. The b passage must surface
    texts={'en': b, 'zh-CN': 'missing'} — never point zh-CN at a's content."""
    en = _doc(
        "en",
        "guide.md",
        (
            "<!-- makewiki:section=a -->\n## A\nEN alpha.\n"
            "\n"
            "<!-- makewiki:section=b -->\n## B\nEN beta.\n"
        ),
    )
    zh = _doc(
        "zh-CN",
        "guide.md",
        "<!-- makewiki:section=a -->\n## A\nZH alpha.\n",
    )

    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents({"en": [en], "zh-CN": [zh]})
    prose = {p.section_id: p for p in passages if p.block_id is None}

    # Section 'a' is present in both.
    assert prose["a"].languages == ["en", "zh-CN"]
    assert prose["a"].texts["en"] == "EN alpha."
    assert prose["a"].texts["zh-CN"] == "ZH alpha."

    # Section 'b' is missing from zh-CN: marked 'missing', never replaced by a's
    # (or any other) content.
    assert prose["b"].document_id == "guide.md"
    assert prose["b"].languages == ["en", "zh-CN"]
    assert prose["b"].texts == {"en": "EN beta.", "zh-CN": "missing"}
    assert prose["b"].review_item_id == "L4b:guide.md:b"


def test_l4b_review_item_id_is_stable():
    """The prose review_item_id is L4b:<document>:<section> and identical across
    the semantic-review / parity paths because both derive from the SAME
    AlignedPassage.review_item_id."""
    en = _doc(
        "en",
        "install.md",
        "<!-- makewiki:section=install -->\n## Install\nEN install prose.\n",
    )
    zh = _doc(
        "zh-CN",
        "install.md",
        "<!-- makewiki:section=install -->\n## 安装\nZH install prose.\n",
    )

    reviewer = CrossLanguageReviewer()
    # semantic-review path and parity path both call align_documents; the id is
    # the same stable string either way.
    first = reviewer.aligned_passages({"en": [en], "zh-CN": [zh]})
    second = reviewer.align_documents({"en": [en], "zh-CN": [zh]})

    p1 = next(p for p in first if p.block_id is None and p.section_id == "install")
    p2 = next(p for p in second if p.block_id is None and p.section_id == "install")
    assert p1.review_item_id == "L4b:install.md:install"
    assert p1.review_item_id == p2.review_item_id


def test_same_section_id_different_documents_do_not_collide():
    """Two documents 'a.md' and 'b.md' both with section id 'install' yield
    SEPARATE AlignedPassages (one per document_id), never a merged one."""
    a_en = _doc("en", "a.md", "<!-- makewiki:section=install -->\n## I\nA-install en.\n")
    a_zh = _doc("zh-CN", "a.md", "<!-- makewiki:section=install -->\n## I\nA-install zh.\n")
    b_en = _doc("en", "b.md", "<!-- makewiki:section=install -->\n## I\nB-install en.\n")
    b_zh = _doc("zh-CN", "b.md", "<!-- makewiki:section=install -->\n## I\nB-install zh.\n")

    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents(
        {"en": [a_en, b_en], "zh-CN": [a_zh, b_zh]}
    )

    install_prose = [p for p in passages if p.block_id is None and p.section_id == "install"]
    # Two distinct passages, one per document — not merged into one.
    assert len(install_prose) == 2
    by_doc = {p.document_id: p for p in install_prose}
    assert set(by_doc) == {"a.md", "b.md"}
    assert by_doc["a.md"].texts == {"en": "A-install en.", "zh-CN": "A-install zh."}
    assert by_doc["b.md"].texts == {"en": "B-install en.", "zh-CN": "B-install zh."}
    assert by_doc["a.md"].review_item_id == "L4b:a.md:install"
    assert by_doc["b.md"].review_item_id == "L4b:b.md:install"


def test_writer_reordered_native_sections_still_pass_alignment():
    """A writer may reorder native sections AND use entirely different H2
    heading text — same stable section IDs still pair every section by ID."""
    en = _doc(
        "en",
        "guide.md",
        (
            "<!-- makewiki:section=install -->\n## Install\nEN install prose.\n"
            "\n"
            "<!-- makewiki:section=config -->\n## Configure\nEN config prose.\n"
            "\n"
            "<!-- makewiki:section=usage -->\n## Use\nEN usage prose.\n"
        ),
    )
    # zh-CN: DIFFERENT order (config/usage/install) and entirely DIFFERENT,
    # non-obvious heading text that bears no relation to the section ids.
    zh = _doc(
        "zh-CN",
        "guide.md",
        (
            "<!-- makewiki:section=config -->\n"
            "## 配置说明\nZH config prose.\n"
            "\n"
            "<!-- makewiki:section=usage -->\n"
            "## 使用教学\nZH usage prose.\n"
            "\n"
            "<!-- makewiki:section=install -->\n"
            "## 安装指南\nZH install prose.\n"
        ),
    )

    reviewer = CrossLanguageReviewer()
    passages = reviewer.align_documents({"en": [en], "zh-CN": [zh]})
    prose = {p.section_id: p for p in passages if p.block_id is None}

    assert set(prose) == {"install", "config", "usage"}
    for section_id in ("install", "config", "usage"):
        assert prose[section_id].languages == ["en", "zh-CN"]
        assert prose[section_id].texts["en"] == f"EN {section_id} prose."
        assert prose[section_id].texts["zh-CN"] == f"ZH {section_id} prose."

