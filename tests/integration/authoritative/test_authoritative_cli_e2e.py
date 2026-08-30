"""Comprehensive end-to-end integration tests for authoritative mechanical CLI commands.

Uses mock LLM fixtures and CLI runner without any Python cognitive generators.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    SemanticAuditVerdict,
    compute_documents_digest,
)

runner = CliRunner()


@pytest.fixture
def sample_setup(tmp_path: Path) -> tuple[Path, Path]:
    proj = tmp_path / "sample_project"
    proj.mkdir()
    (proj / "Makefile").write_text(
        ".PHONY: build test\nbuild:\n\tgcc -o app main.c\ntest:\n\tmake -q\n",
        encoding="utf-8",
    )
    (proj / "config.yaml").write_text("server:\n  port: 8080\n", encoding="utf-8")
    (proj / "pyproject.toml").write_text(
        '[project]\nname="myapp"\nversion="1.0.0"\n\n[project.scripts]\nmyapp="cli:main"\n',
        encoding="utf-8",
    )
    (proj / "cli.py").write_text(
        'import typer\napp = typer.Typer()\n\n'
        '@app.command()\ndef run(port: int = 8080, host: str = "0.0.0.0"):\n    print(port)\n\n'
        '@app.command()\ndef serve():\n    print("s")\n\n'
        'def main():\n    app()\n',
        encoding="utf-8",
    )
    (proj / "README.md").write_text("# myapp\n\nmyapp is a tiny app.\n", encoding="utf-8")

    wiki = tmp_path / "makewiki"
    wiki.mkdir()

    en_content = (
        "# myapp\n\n"
        "myapp is a tiny app.\n\n"
        "<!-- makewiki:section=build -->\n"
        "## Build\n\n"
        "[[id:build]]\n```bash\nmake build\n```\n\n"
        "<!-- makewiki:section=test -->\n"
        "## Test\n\n"
        "[[id:test]]\n```bash\nmake test\n```\n\n"
        "<!-- makewiki:section=run -->\n"
        "## Run\n\n"
        "[[id:run]]\n```bash\nmyapp run --port 8080\n```\n\n"
        "<!-- makewiki:section=config -->\n"
        "## Configure\n\n"
        "Set `server.port` in `./config.yaml`.\n"
    )
    zh_content = (
        "# myapp\n\n"
        "myapp 是一个微型应用。\n\n"
        "<!-- makewiki:section=build -->\n"
        "## 构建\n\n"
        "[[id:build]]\n```bash\nmake build\n```\n\n"
        "<!-- makewiki:section=test -->\n"
        "## 测试\n\n"
        "[[id:test]]\n```bash\nmake test\n```\n\n"
        "<!-- makewiki:section=run -->\n"
        "## 运行\n\n"
        "[[id:run]]\n```bash\nmyapp run --port 8080\n```\n\n"
        "<!-- makewiki:section=config -->\n"
        "## 配置\n\n"
        "在 `./config.yaml` 中设置 `server.port`。\n"
    )
    (wiki / "README.md").write_text(en_content, encoding="utf-8")
    (wiki / "README.zh-CN.md").write_text(zh_content, encoding="utf-8")

    return proj, wiki


def test_census_cli_runs_and_emits_json(sample_setup: tuple[Path, Path]):
    proj, _ = sample_setup
    res = runner.invoke(app, ["census", str(proj), "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["project"] == "sample_project"
    assert data["source_files"] >= 0


def test_evidence_and_scan_alias_cli(sample_setup: tuple[Path, Path]):
    proj, _ = sample_setup
    res = runner.invoke(app, ["evidence", str(proj), "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["detection"]["project_name"] == "myapp"
    assert data["total_facts"] >= 3

    # Test scan alias
    res_alias = runner.invoke(app, ["scan", str(proj), "--format", "json"])
    assert res_alias.exit_code == 0


def test_coverage_cli_runs(sample_setup: tuple[Path, Path]):
    proj, _ = sample_setup
    res = runner.invoke(app, ["coverage", str(proj), "--format", "json"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["files_discovered"] >= 4
    assert data["manifests_discovered"] == 1


def test_validate_cli_passes_on_valid_docs(sample_setup: tuple[Path, Path]):
    _, wiki = sample_setup
    res = runner.invoke(app, ["validate", str(wiki)])
    assert res.exit_code == 0


def test_review_cli_passes(sample_setup: tuple[Path, Path]):
    _, wiki = sample_setup
    res_review = runner.invoke(app, ["review", str(wiki)])
    assert res_review.exit_code == 0


def test_build_site_cli(sample_setup: tuple[Path, Path], tmp_path: Path):
    _, wiki = sample_setup
    site_out = tmp_path / "site_out"
    res = runner.invoke(app, ["build-site", str(wiki), "--output", str(site_out)])
    assert res.exit_code == 0
    assert (site_out / "index.html").exists()


def test_export_cli_html_and_epub(sample_setup: tuple[Path, Path]):
    _, wiki = sample_setup
    res_html = runner.invoke(app, ["export", str(wiki), "--format", "html"])
    assert res_html.exit_code == 0
    assert (wiki / "export" / "documentation.html").exists()

    res_epub = runner.invoke(app, ["export", str(wiki), "--format", "epub"])
    assert res_epub.exit_code == 0
    assert (wiki / "export" / "documentation.epub").exists()

    # Reject PDF
    res_pdf = runner.invoke(app, ["export", str(wiki), "--format", "pdf"])
    assert res_pdf.exit_code != 0


def test_sync_bundle_cli_confluence_and_notion(sample_setup: tuple[Path, Path]):
    _, wiki = sample_setup
    res_conf = runner.invoke(app, ["sync-bundle", str(wiki), "--target", "confluence"])
    assert res_conf.exit_code == 0
    assert (wiki / "sync" / "confluence" / "en" / "manifest.json").exists()

    res_notion = runner.invoke(app, ["sync-bundle", str(wiki), "--target", "notion"])
    assert res_notion.exit_code == 0
    assert (wiki / "sync" / "notion" / "en" / "manifest.json").exists()


def test_verify_docs_cli_with_and_without_semantic_audit(sample_setup: tuple[Path, Path], tmp_path: Path):
    proj, wiki = sample_setup
    # 1. Without semantic audit -> reports pending_semantic_review (exit code 0 under default allow_pending_llm_layers=true)
    res = runner.invoke(
        app,
        ["verify-docs", str(proj), "--wiki-dir", str(wiki), "--format", "json"],
    )
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["quality_gate"]["verdict"] == "pending_semantic_review"

    # 2. Provide a matching SemanticAuditBundle from LLM Auditor
    doc_paths = sorted(wiki.glob("*.md"))
    digest = compute_documents_digest(doc_paths)
    review_items = [item["review_item_id"] for item in data["report"].get("review_items", [])]

    verdicts = [
        SemanticAuditVerdict(
            review_item_id=item_id,
            layer="L4b" if item_id.startswith("L4b") else ("L3" if item_id.startswith("L3") else "L5"),
            status="passed",
            rationale_summary="Adjudicated and verified consistent.",
        )
        for item_id in review_items
    ]
    audit_bundle = SemanticAuditBundle(
        documents_digest=digest,
        auditor="LLM Auditor",
        verdicts=verdicts,
    )
    bundle_file = tmp_path / "audit_bundle.json"
    bundle_file.write_text(audit_bundle.model_dump_json(indent=2), encoding="utf-8")

    res_audited = runner.invoke(
        app,
        [
            "verify-docs",
            str(proj),
            "--wiki-dir", str(wiki),
            "--semantic-audit", str(bundle_file),
            "--format", "json",
        ],
    )
    assert res_audited.exit_code == 0
    data_audited = json.loads(res_audited.stdout)
    assert data_audited["quality_gate"]["verdict"] == "passed"
    assert data_audited["quality_gate"]["passed"] is True
