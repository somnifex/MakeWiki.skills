"""CLI regression tests for verify-docs / verify honest rendering + exit codes.

Covers audit finding #2 (the human CLI must render the honest verdict and each
layer's verdict with DISTINCT markers, and never print PASS while any layer is
pending) and finding #8 (verify-docs routes the honest verdict to
``result.ci_exit_code`` and exits with it; ``--semantic-audit`` opts in to the
LLM audit bundle).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.verification.semantic_audit import SemanticAuditBundle


def _plain(text: str) -> str:
    """Strip Rich/Typer ANSI colour codes from rendered output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _make_wiki(tmp_path: Path, content: str | None = None) -> Path:
    """Build a tiny project with a makewiki/ output for verify-docs."""
    project = tmp_path / "project"
    wiki = project / "makewiki"
    wiki.mkdir(parents=True)
    (wiki / "README.md").write_text(
        content if content is not None else "# My Project\n\n## Build\nrun it\n",
        encoding="utf-8",
    )
    return project


def test_verify_docs_renders_pend_not_pass_for_pending_layer(tmp_path: Path):
    """With no semantic audit, the semantic layers are PENDING and the CLI must
    print PEND — never PASS — for them, and the gate line must not be a PASS.

    The process exits with the honest ``ci_exit_code`` (here 3, pending
    mechanical L1/L2 in a bare wiki), never the old passed-bool exit 0.
    """
    project = _make_wiki(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["verify-docs", str(project)])
    plain = _plain(result.output or "")
    combined = plain + _plain(result.stderr or "")
    # The pending semantic layers (L3/L4b/L5) render PEND, and the pending
    # mechanical layers (L1/L2) render PEND too — never PASS.
    assert "L3" in combined
    assert plain.count("PEND") >= 2
    # A PENDING layer's line is never rendered PASS: every '<marker> PASS'
    # must belong to a passed layer (L0/L4a here), and the GATE verdict line
    # must read PEND, never PASS.
    gate_line = next((ln for ln in plain.splitlines() if "Gate verdict" in ln), "")
    assert "PASS" not in gate_line, f"gate verdict printed PASS while pending: {gate_line!r}"
    assert "pending" in gate_line
    # Mechanical layers L1/L2 are pending here -> ci_exit_code 3 (the honest
    # routing), NOT the old passed-bool exit 0.
    assert result.exit_code == 3


def test_verify_docs_semantic_audit_flag_is_documented_in_help(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["verify-docs", "--help"])
    assert result.exit_code == 0
    assert "--semantic-audit" in _plain(result.output)

    # The alias `verify` exposes the same flag.
    result_alias = runner.invoke(app, ["verify", "--help"])
    assert "--semantic-audit" in _plain(result_alias.output)


def test_verify_docs_merges_semantic_audit_when_flag_given(tmp_path: Path):
    project = _make_wiki(tmp_path)
    wiki = project / "makewiki"
    doc_paths = sorted(wiki.rglob("*.md"))

    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditVerdict,
        compute_documents_digest,
    )

    bundle = SemanticAuditBundle(
        documents_digest=compute_documents_digest(doc_paths),
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:1", layer="L3", status="passed",
                rationale_summary="ok",
            ),
            SemanticAuditVerdict(
                review_item_id="L4b:1", layer="L4b", status="passed",
                rationale_summary="ok",
            ),
            SemanticAuditVerdict(
                review_item_id="L5:1", layer="L5", status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps(bundle.model_dump()), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["verify-docs", str(project), "--semantic-audit", str(audit_file), "--format", "json"],
    )
    # The bare wiki's mechanical L1/L2 are pending -> honest ci_exit_code 3.
    # The semantic layers, however, WERE merged: none are pending any more.
    assert result.exit_code == 3, result.output
    payload = json.loads(result.stdout)
    gate = payload["quality_gate"]
    assert gate["ci_exit_code"] == 3
    assert gate["l3_status"] == "passed"
    assert gate["l4b_status"] == "passed"
    assert gate["l5_status"] == "passed"
    assert gate["pending_llm_layers"] == []
    assert gate["semantic_complete"] is True


def test_verify_docs_stale_semantic_audit_leaves_layers_pending(tmp_path: Path):
    project = _make_wiki(tmp_path)
    # Deliberately wrong digest -> stale bundle -> NOT merged -> pending.
    bundle = SemanticAuditBundle(
        documents_digest="sha256:deadbeef",
        verdicts=[
            {
                "review_item_id": "L3:1", "layer": "L3", "status": "passed",
                "rationale_summary": "ok",
            }
        ],
    )
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps(bundle.model_dump()), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["verify-docs", str(project), "--semantic-audit", str(audit_file), "--format", "json"],
    )
    assert result.exit_code in (0, 3), result.output
    payload = json.loads(result.stdout)
    gate = payload["quality_gate"]
    # Untouched semantic layers stay pending; gate is NOT passed.
    assert gate["passed"] is False
    assert "L3" in gate["pending_llm_layers"]
