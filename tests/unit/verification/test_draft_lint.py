"""Tests for the Integration draft-hygiene lint (mechanical checks only)."""

from pathlib import Path

from makewiki_skills.model.documentation_model import (
    DocumentationGap,
    DocumentationModel,
    InterfaceDisposition,
)
from makewiki_skills.model.documentation_plan import (
    DocumentationPlan,
    DocumentationSection,
)
from makewiki_skills.model.page_spec import PageSpec
from makewiki_skills.verification.draft_lint import run_draft_lint


def _make_plan(pages: list[str], languages: list[str] | None = None) -> DocumentationPlan:
    return DocumentationPlan(
        sections=[
            DocumentationSection(id="s1", title_intent="t", pages=sorted(pages))
        ],
    )


def _spec(page_id: str, required: list[str] | None = None) -> PageSpec:
    return PageSpec(
        page_id=page_id,
        page_type="how_to",
        title_intent="t",
        audience=["user"],
        user_goal="g",
        required_sections=required or ["overview"],
    )


def _doc_model(dispositions: list[InterfaceDisposition], gap_ids: list[str]) -> DocumentationModel:
    return DocumentationModel(
        interface_dispositions=dispositions,
        documentation_gaps=[
            DocumentationGap(id=g, severity="minor", reason="r") for g in gap_ids
        ],
    )


def _write_pair(wiki: Path, base: str, en: str, zh: str) -> None:
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / f"{base}.md").parent.mkdir(parents=True, exist_ok=True)
    (wiki / f"{base}.md").write_text(en, encoding="utf-8")
    (wiki / f"{base}.zh-CN.md").write_text(zh, encoding="utf-8")


def test_clean_drafts_pass(tmp_path: Path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    en = (
        "<!-- makewiki:section=overview -->\n## Overview\n\ntext\n\n"
        "<!-- makewiki:section=related -->\n## Related\n"
    )
    zh = en  # same markers
    _write_pair(wiki, "user/tokens", en, zh)
    plan = _make_plan(["user/tokens"])
    specs = [_spec("user/tokens", ["overview", "related"])]

    issues = run_draft_lint(wiki, plan, specs, None, ["en", "zh-CN"])
    assert [i for i in issues if i.severity == "error"] == []


def test_frontmatter_leak_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = (
        "---\npage_id: user/tokens\naudience: [user]\n---\n\n"
        "<!-- makewiki:section=overview -->\n## Overview\n"
    )
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], None, ["en", "zh-CN"])
    rules = {i.rule for i in issues}
    assert "frontmatter_leak" in rules


def test_non_writer_frontmatter_allowed(tmp_path: Path):
    """Frontmatter without writer-echo keys is not a lint error (renderer strips it)."""
    wiki = tmp_path / "wiki"
    body = "---\ntitle: Some Page\n---\n\n<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], None, ["en", "zh-CN"])
    assert "frontmatter_leak" not in {i.rule for i in issues}


def test_internal_artifact_path_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = (
        "<!-- makewiki:section=overview -->\n## Overview\n\n"
        "See claims: .makewiki-artifacts/04-claim-bundles/claims.user.yaml\n"
    )
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], None, ["en", "zh-CN"])
    assert "artifact_path_leak" in {i.rule for i in issues}


def test_missing_required_marker_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    issues = run_draft_lint(
        wiki, plan, [_spec("user/tokens", ["overview", "reveal"])], None, ["en", "zh-CN"]
    )
    missing = [i for i in issues if i.rule == "required_section_missing"]
    assert any("reveal" in i.message for i in missing)


def test_duplicate_block_id_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = (
        "<!-- makewiki:section=overview -->\n## Overview\n\n"
        "[[id:blk-a]]\n```bash\necho 1\n```\n\n"
        "[[id:blk-a]]\n```bash\necho 2\n```\n"
    )
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], None, ["en", "zh-CN"])
    assert "duplicate_block_id" in {i.rule for i in issues}


def test_block_id_set_mismatch_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    en = "<!-- makewiki:section=overview -->\n## Overview\n\n[[id:blk-a]]\n```bash\necho 1\n```\n"
    zh = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", en, zh)
    plan = _make_plan(["user/tokens"])
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], None, ["en", "zh-CN"])
    mismatch = [i for i in issues if i.rule == "block_id_set_mismatch"]
    assert any("blk-a" in i.message for i in mismatch)


def test_disposition_unknown_page_fails(tmp_path: Path):
    """The exact benchmark defect: disposition page_id not in the plan."""
    wiki = tmp_path / "wiki"
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    dm = _doc_model(
        [
            InterfaceDisposition(
                operation_id="token.create", disposition="documented", page_id="reference/api/token"
            )
        ],
        [],
    )
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], dm, ["en", "zh-CN"])
    bad = [i for i in issues if i.rule == "disposition_unknown_page"]
    assert any("reference/api/token" in i.message for i in bad)


def test_disposition_duplicate_operation_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    dm = _doc_model(
        [
            InterfaceDisposition(operation_id="token.create", disposition="omitted", reason="niche"),
            InterfaceDisposition(operation_id="token.create", disposition="omitted", reason="dup"),
        ],
        [],
    )
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], dm, ["en", "zh-CN"])
    assert "disposition_duplicate_operation" in {i.rule for i in issues}


def test_disposition_omitted_and_unresolved_pass(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    dm = _doc_model(
        [
            InterfaceDisposition(operation_id="op.a", disposition="omitted", reason="internal-only"),
            InterfaceDisposition(operation_id="op.b", disposition="unresolved", gap_id="gap.1"),
        ],
        ["gap.1"],
    )
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], dm, ["en", "zh-CN"])
    assert [i for i in issues if i.rule.startswith("disposition_")] == []


def test_disposition_unknown_gap_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "user/tokens", body, body)
    plan = _make_plan(["user/tokens"])
    dm = _doc_model(
        [InterfaceDisposition(operation_id="op.b", disposition="unresolved", gap_id="gap.missing")],
        [],
    )
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], dm, ["en", "zh-CN"])
    assert "disposition_unknown_gap" in {i.rule for i in issues}


def test_planned_page_missing_draft_fails(tmp_path: Path):
    wiki = tmp_path / "wiki"
    (wiki / "user").mkdir(parents=True)
    (wiki / "user" / "tokens.md").write_text(
        "<!-- makewiki:section=overview -->\n## Overview\n", encoding="utf-8"
    )
    plan = _make_plan(["user/tokens"])  # zh draft missing
    issues = run_draft_lint(wiki, plan, [_spec("user/tokens")], None, ["en", "zh-CN"])
    assert any(
        i.rule == "planned_page_missing_draft" and "zh-CN" in i.message for i in issues
    )


# ---- generic declared-language resolution (filename contract) ---------------


def test_case1_en_ja_pass(tmp_path: Path):
    """en + ja: plain .md = en, guide.ja.md = ja; both drafts present -> pass."""
    wiki = tmp_path / "wiki"
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    _write_pair(wiki, "guide", body, body)
    (wiki / "guide.ja.md").write_text(body, encoding="utf-8")
    plan = _make_plan(["guide"])
    issues = run_draft_lint(wiki, plan, [_spec("guide")], None, ["en", "ja"])
    assert [i for i in issues if i.severity == "error"] == []


def test_case2_three_languages_block_id_mismatch_names_language(tmp_path: Path):
    """en + de + fr with consistent block IDs pass; a missing ID in fr is
    reported against fr explicitly."""
    wiki = tmp_path / "wiki"
    en = (
        "<!-- makewiki:section=overview -->\n## Overview\n\n"
        "[[id:blk-a]]\n```bash\necho 1\n```\n"
    )
    de = en
    fr_ok = en
    _write_pair(wiki, "guide", en, de)  # guide.md + guide.de.md
    (wiki / "guide.fr.md").write_text(fr_ok, encoding="utf-8")
    plan = _make_plan(["guide"])
    issues = run_draft_lint(wiki, plan, [_spec("guide")], None, ["en", "de", "fr"])
    assert [i for i in issues if i.rule == "block_id_set_mismatch"] == []

    fr_missing = "<!-- makewiki:section=overview -->\n## Overview\n"
    (wiki / "guide.fr.md").write_text(fr_missing, encoding="utf-8")
    issues = run_draft_lint(wiki, plan, [_spec("guide")], None, ["en", "de", "fr"])
    mismatches = [i for i in issues if i.rule == "block_id_set_mismatch"]
    assert any("fr" in i.document for i in mismatches), mismatches
    assert any("'blk-a'" in i.message and "fr" in i.message for i in mismatches)


def test_case3_non_english_default_not_forced_to_en(tmp_path: Path):
    """default_language=ja: guide.md is ja, guide.en.md is en — never forced
    into an 'en' bucket."""
    from makewiki_skills.review.localized_filename import resolve_localized_filename

    resolved_plain = resolve_localized_filename("guide.md", ["ja", "en"], "ja")
    assert resolved_plain.language == "ja"
    assert resolved_plain.base_id == "guide"
    resolved_en = resolve_localized_filename("guide.en.md", ["ja", "en"], "ja")
    assert resolved_en.language == "en"
    assert resolved_en.base_id == "guide"

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    (wiki / "guide.md").write_text(body, encoding="utf-8")
    (wiki / "guide.en.md").write_text(body, encoding="utf-8")
    plan = _make_plan(["guide"])
    issues = run_draft_lint(
        wiki, plan, [_spec("guide")], None, ["ja", "en"], default_language="ja"
    )
    # Both declared-language drafts present: no missing-draft error.
    assert [i for i in issues if i.rule == "planned_page_missing_draft"] == []


def test_case4_planned_page_missing_one_declared_language_fails(tmp_path: Path):
    """en + de + fr where only en and de drafts exist: fr is reported, and no
    declared language other than fr is invented as missing."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    (wiki / "guide.md").write_text(body, encoding="utf-8")  # en (default)
    (wiki / "guide.de.md").write_text(body, encoding="utf-8")
    plan = _make_plan(["guide"])
    issues = run_draft_lint(wiki, plan, [_spec("guide")], None, ["en", "de", "fr"])
    missing = [i for i in issues if i.rule == "planned_page_missing_draft"]
    assert any("language 'fr'" in i.message for i in missing), missing
    assert not any("language 'en'" in i.message or "language 'de'" in i.message for i in missing)


def test_case5_undeclared_suffix_gets_no_language_semantics(tmp_path: Path):
    """A .xx.md file matching no declared language: it is simply the plain
    default-language document 'guide.xx' — no language is guessed, and it
    never joins 'guide''s cross-language group."""
    from makewiki_skills.review.localized_filename import resolve_localized_filename

    resolved = resolve_localized_filename("guide.xx.md", ["en", "ja"], "en")
    assert resolved.language == "en"  # the plain .md form, NOT a guess of xx
    assert resolved.base_id == "guide.xx"  # its own document, suffix intact
    assert resolved.base_id != "guide"  # never merged with guide's group

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    body = "<!-- makewiki:section=overview -->\n## Overview\n\n[[id:blk-a]]\n```bash\necho 1\n```\n"
    (wiki / "guide.md").write_text(body, encoding="utf-8")  # en (default)
    (wiki / "guide.ja.md").write_text(body, encoding="utf-8")  # ja, same IDs
    (wiki / "guide.xx.md").write_text(
        "<!-- makewiki:section=overview -->\n## Overview\n",  # no block ID
        encoding="utf-8",
    )
    plan = _make_plan(["guide"])
    issues = run_draft_lint(wiki, plan, [_spec("guide")], None, ["en", "ja"])
    # The undeclared file's divergent content must NOT create a block-ID
    # mismatch against the declared pair (it is a separate document).
    assert [i for i in issues if i.rule == "block_id_set_mismatch"] == []
    # ...and no invented language is reported missing.
    assert [i for i in issues if i.rule == "planned_page_missing_draft"] == []


def test_plan_languages_win_over_caller_arguments(tmp_path: Path):
    """The canonical DocumentationPlan.languages drives resolution when
    present, overriding caller-passed legacy sets."""
    from makewiki_skills.model.documentation_plan import DocumentationPlan, DocumentationSection

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    body = "<!-- makewiki:section=overview -->\n## Overview\n"
    (wiki / "guide.md").write_text(body, encoding="utf-8")
    (wiki / "guide.ja.md").write_text(body, encoding="utf-8")
    plan = DocumentationPlan(
        sections=[DocumentationSection(id="s1", title_intent="t", pages=["guide"])],
        languages=["en", "ja"],
    )
    # Caller passes the legacy pair; the plan's en+ja must win (no zh-CN draft
    # is demanded, and the ja draft is recognized).
    issues = run_draft_lint(wiki, plan, [_spec("guide")], None, ["en", "zh-CN"])
    assert [i for i in issues if i.rule == "planned_page_missing_draft"] == []
