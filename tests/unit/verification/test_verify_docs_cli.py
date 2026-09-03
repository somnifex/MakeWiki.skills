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
    """verify-docs --semantic-audit merges a REAL bundle item-level.

    The bundle's review_item_ids are the ones Python actually computed: first run
    verify-docs with an empty-verdict probe so the JSON report exposes its
    ``review_items`` registry, then build a bundle that adjudicates EXACTLY those
    ids as passed and re-run. The merged layers reflect the audit: the semantic
    layers are no longer pending."""
    project = _make_wiki(tmp_path)
    wiki = project / "makewiki"
    doc_paths = sorted(wiki.rglob("*.md"))

    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditVerdict,
        compute_documents_digest,
    )

    runner = CliRunner()

    def run_with(bundle) -> dict:
        audit_file = tmp_path / "audit.json"
        audit_file.write_text(json.dumps(bundle.model_dump()), encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "verify-docs", str(project), "--semantic-audit", str(audit_file),
                "--format", "json",
            ],
        )
        assert result.exit_code == 3, result.output  # bare wiki mechanical pending
        return json.loads(result.stdout)

    # 1) Probe: valid digest + empty verdicts -> Python computes the registry of
    # pending semantic review items and exposes it in the JSON report.
    probe = SemanticAuditBundle(
        documents_digest=compute_documents_digest(doc_paths), verdicts=[]
    )
    probe_payload = run_with(probe)
    review_items = probe_payload["report"]["review_items"]
    assert review_items, "expected a computed review_items registry"
    assert all(ri["status"] == "pending" for ri in review_items)

    # 2) Build a COMPLETE bundle adjudicating every real review item as passed.
    full = SemanticAuditBundle(
        documents_digest=compute_documents_digest(doc_paths),
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=ri["review_item_id"],
                layer=ri["layer"],
                status="passed",
                rationale_summary="ok",
            )
            for ri in review_items
        ],
    )
    payload = run_with(full)
    gate = payload["quality_gate"]
    # The bare wiki's mechanical L1/L2 are pending -> honest ci_exit_code 3.
    # The semantic layers, however, WERE merged: none are pending any more.
    assert gate["ci_exit_code"] == 3
    assert gate["l3_status"] == "passed"
    assert gate["l4b_status"] == "passed"
    assert gate["l5_status"] == "passed"
    assert gate["pending_llm_layers"] == []
    assert gate["semantic_complete"] is True


def test_verify_docs_unknown_review_item_id_not_merged(tmp_path: Path):
    """A bundle whose verdict references an UNKNOWN review_item_id (matching no
    real pending semantic check) is REJECTED wholesale: L3 stays pending and the
    gate is not passed."""
    project = _make_wiki(tmp_path)
    wiki = project / "makewiki"
    doc_paths = sorted(wiki.rglob("*.md"))

    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditVerdict,
        compute_documents_digest,
    )

    # A VALID, fresh documents_digest, but an unknown/fake review_item_id.
    bundle = SemanticAuditBundle(
        documents_digest=compute_documents_digest(doc_paths),
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:1", layer="L3", status="passed",
                rationale_summary="ok",
            )
        ],
    )
    audit_file = tmp_path / "audit.json"
    audit_file.write_text(json.dumps(bundle.model_dump()), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "verify-docs", str(project), "--semantic-audit", str(audit_file),
            "--format", "json",
        ],
    )
    payload = json.loads(result.stdout)
    gate = payload["quality_gate"]
    # The unknown-id verdict cannot adjudicate anything -> L3 stays pending and
    # the whole bundle is not silently trusted.
    assert gate["passed"] is False
    assert gate["l3_status"] == "pending"
    assert "L3" in gate["pending_llm_layers"]
    assert gate["semantic_complete"] is False


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


def test_verify_docs_human_output_aggregates_repeated_findings(tmp_path: Path):
    """Repeated same-kind mechanical findings collapse into one summary row.

    Display aggregation only: the JSON output still carries every individual
    finding, and the human report names the count instead of repeating the
    row hundreds of times.
    """
    content = (
        "# My Project\n\n## Build\n\n"
        + "\n".join(
            f"See `./missing_dir_{i}/file.py` for step {i}." for i in range(12)
        )
    )
    project = _make_wiki(tmp_path, content)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["verify-docs", str(project), "--wiki-dir", str(project / "makewiki"), "--lang", "en"],
    )
    human = _plain(result.output)
    assert "aggregated" in human
    # The count of identical-shape findings is shown, not 12 separate rows:
    # the aggregated table renders a "12" count cell, the reason once, and at
    # most 3 example lines.
    assert "12" in human
    assert human.count("./missing_dir_") <= 5  # reason representative + 3 examples
    # None of the other findings' lines appear individually.
    assert "./missing_dir_7" not in human
    assert "./missing_dir_11" not in human
    # JSON keeps every finding.
    result_json = runner.invoke(
        app,
        ["verify-docs", str(project), "--wiki-dir", str(project / "makewiki"), "--lang", "en", "--format", "json"],
    )
    payload = json.loads(result_json.output)
    l1_path_failures = [
        c
        for c in payload["report"]["layers"]["L1"]["checks"]
        if c["status"] == "failed" and c["claim_type"] == "path"
    ]
    assert len(l1_path_failures) == 12
