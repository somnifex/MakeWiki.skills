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
