"""CLI regression tests for `makewiki lint-drafts`.

Covers the fail-closed full Integration mode (missing/invalid canonical V3
artifacts block instead of silently degrading to a structural-only pass),
the explicit ``--structural-only`` opt-in, the artifact-root discovery rule,
and the DocumentationModel CLI wiring for the disposition cross-checks.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from makewiki_skills.cli import app, resolve_artifact_target


def _plain(text: str) -> str:
    """Strip Rich/Typer ANSI colour codes from rendered output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text or "")


_DRAFT_BODY = "<!-- makewiki:section=overview -->\n## Overview\n\ntext\n"

_PLAN = {
    "documentation_plan": {
        "sections": [
            {"id": "s1", "title_intent": "Section", "pages": ["user/tokens"]}
        ]
    }
}

_SPECS = {
    "page_specs": {
        "specs": [
            {
                "page_id": "user/tokens",
                "page_type": "how_to",
                "title_intent": "Tokens",
                "audience": ["user"],
                "user_goal": "Manage tokens",
                "required_sections": ["overview"],
            }
        ]
    }
}

_VALID_DOC_MODEL = {
    "documentation_model": {
        "interface_dispositions": []
    }
}

_VALID_DOC_MODEL = {
    "documentation_model": {
        "interface_dispositions": [
            {"operation_id": "token.create", "disposition": "documented", "page_id": "user/tokens"}
        ]
    }
}


def _write_wiki(wiki: Path) -> None:
    (wiki / "user").mkdir(parents=True, exist_ok=True)
    (wiki / "user" / "tokens.md").write_text(_DRAFT_BODY, encoding="utf-8")
    (wiki / "user" / "tokens.zh-CN.md").write_text(_DRAFT_BODY, encoding="utf-8")


def _write_artifacts(
    target: Path,
    *,
    plan: dict | None | str = _PLAN,
    specs: dict | None | str = _SPECS,
    doc_model: dict | None | str = _VALID_DOC_MODEL,
) -> None:
    """Write the canonical artifact tree under ``target``.

    ``None`` removes the artifact (its directory stays absent); a ``str``
    writes that raw text (malformed content). Defaults give a complete,
    valid tree.
    """
    arts = target / ".makewiki-artifacts"
    plan_dir = arts / "10-documentation-plan"
    if plan is None:
        plan_dir.mkdir(parents=True, exist_ok=True)
    else:
        plan_dir.mkdir(parents=True, exist_ok=True)
        body = plan if isinstance(plan, str) else yaml.safe_dump(plan)
        (plan_dir / "documentation_plan.yaml").write_text(body, encoding="utf-8")

    spec_dir = arts / "11-page-specs"
    if specs is None:
        spec_dir.mkdir(parents=True, exist_ok=True)
    else:
        spec_dir.mkdir(parents=True, exist_ok=True)
        body = specs if isinstance(specs, str) else yaml.safe_dump(specs)
        (spec_dir / "page_specs.user.yaml").write_text(body, encoding="utf-8")

    model_dir = arts / "07-documentation-model"
    if doc_model is None:
        model_dir.mkdir(parents=True, exist_ok=True)
    else:
        model_dir.mkdir(parents=True, exist_ok=True)
        body = doc_model if isinstance(doc_model, str) else yaml.safe_dump(doc_model)
        (model_dir / "documentation_model.yaml").write_text(body, encoding="utf-8")


# ---- CASE A: default layout, no makewiki.config.yaml -----------------------


def test_case_a_artifacts_in_project_root_discovered_without_config(tmp_path: Path):
    """project/.makewiki-artifacts + project/makewiki, no config file: the
    lint resolves the project root and loads the full artifact context."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project)
    assert resolve_artifact_target(wiki) == project

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert "unavailable" not in plain, plain
    assert result.exit_code == 0, plain


# ---- CASE B: wiki_dir itself is the target root -----------------------------


def test_case_b_wiki_dir_is_target_root(tmp_path: Path):
    """target/.makewiki-artifacts + target/docs: the wiki dir is its own root."""
    target = tmp_path / "target"
    wiki = target / "docs"
    _write_wiki(wiki)
    _write_artifacts(target)
    assert resolve_artifact_target(wiki) == target

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    assert result.exit_code == 0, _plain(result.output)


# ---- CASE C: artifact tree absent -------------------------------------------


def test_case_c_missing_artifact_tree_reports_unavailable(tmp_path: Path):
    """No .makewiki-artifacts anywhere: explicit failure, not a fake pass."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert "artifact context unavailable" in plain, plain
    assert "Draft lint passed" not in plain
    assert result.exit_code != 0


# ---- DocumentationModel CLI wiring (P0 regression) --------------------------


def test_cli_loads_documentation_model_and_flags_unknown_disposition_page(tmp_path: Path):
    """The CLI production path loads the DocumentationModel artifact and runs
    the disposition cross-checks: a documented disposition pointing at an
    unplanned page_id is a blocking error (exit non-zero)."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(
        project,
        doc_model={
            "documentation_model": {
                "interface_dispositions": [
                    {
                        "operation_id": "token.create",
                        "disposition": "documented",
                        "page_id": "reference/api/token",
                    }
                ]
            }
        },
    )

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "disposition_unknown_page" in plain, plain


def test_cli_valid_dispositions_produce_no_disposition_errors(tmp_path: Path):
    """With valid dispositions (planned page / documented gap), the CLI lint
    passes with no disposition_* findings — proving the loader feeds the
    checker rather than skipping it."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(
        project,
        doc_model={
            "documentation_model": {
                "interface_dispositions": [
                    {
                        "operation_id": "token.create",
                        "disposition": "documented",
                        "page_id": "user/tokens",
                    },
                    {
                        "operation_id": "op.internal",
                        "disposition": "unresolved",
                        "gap_id": "gap.1",
                    },
                ],
                "documentation_gaps": [
                    {"id": "gap.1", "severity": "minor", "reason": "internal"}
                ],
            }
        },
    )

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code == 0, plain
    assert "disposition_" not in plain, plain


# ---- Fail-closed Integration mode (CASE 1-9) --------------------------------


def test_case1_complete_artifact_tree_passes(tmp_path: Path):
    """Valid plan + model + specs + drafts -> exit 0."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project)

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    assert result.exit_code == 0, _plain(result.output)
    assert "Draft lint passed" in _plain(result.output)


def test_case2_missing_plan_blocks(tmp_path: Path):
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project, plan=None)

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "documentation_plan_missing" in plain, plain
    assert "Draft lint passed" not in plain


def test_case3_malformed_plan_blocks(tmp_path: Path):
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project, plan="documentation_plan:\n  bogus_field: true\n")

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "documentation_plan_invalid" in plain, plain
    assert "Draft lint passed" not in plain


def test_case4_missing_page_specs_with_planned_pages_blocks(tmp_path: Path):
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project, specs=None)

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "page_specs_missing" in plain, plain
    assert "Draft lint passed" not in plain


def test_case5_malformed_page_spec_blocks(tmp_path: Path):
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project, specs="page_specs:\n  specs:\n  - page_id: x\n    bogus: true\n")

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "page_spec_invalid" in plain, plain
    assert "Draft lint passed" not in plain


def test_case6_missing_documentation_model_blocks(tmp_path: Path):
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project, doc_model=None)

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "documentation_model_missing" in plain, plain
    assert "Draft lint passed" not in plain


def test_case7_malformed_documentation_model_blocks(tmp_path: Path):
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)
    _write_artifacts(project, doc_model="documentation_model:\n  bogus_field: true\n")

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "documentation_model_invalid" in plain, plain
    assert "Draft lint passed" not in plain


def test_case8_structural_only_without_artifacts_passes(tmp_path: Path):
    """Explicit --structural-only with no artifact context: valid Markdown
    passes, and the output says the cross-artifact checks were not run."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    _write_wiki(wiki)

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki), "--structural-only"])
    plain = _plain(result.output)
    assert result.exit_code == 0, plain
    assert "cross-artifact checks were not run" in plain, plain
    assert "Draft lint passed" not in plain


def test_case9_structural_only_still_flags_markdown_defects(tmp_path: Path):
    """--structural-only with a frontmatter leak: exit non-zero."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    leaky = (
        "---\npage_id: user/tokens\naudience: [user]\n---\n\n"
        "<!-- makewiki:section=overview -->\n## Overview\n"
    )
    (wiki / "user").mkdir(parents=True, exist_ok=True)
    (wiki / "user" / "tokens.md").write_text(leaky, encoding="utf-8")
    (wiki / "user" / "tokens.zh-CN.md").write_text(leaky, encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["lint-drafts", str(wiki), "--structural-only"])
    plain = _plain(result.output)
    assert result.exit_code != 0, plain
    assert "frontmatter_leak" in plain, plain
    assert "passed" not in plain.lower()
