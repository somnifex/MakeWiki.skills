"""Unit tests for VerificationOrchestrator."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.orchestrator import VerificationOrchestrator


def test_orchestrator_runs_all_layers(tmp_path: Path):
    (tmp_path / "Makefile").write_text("build:\n\techo build\n", encoding="utf-8")

    doc_en = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# My Project\n\n<!-- makewiki:section=build -->\n## Build\n[[id:build]]\n```bash\nmake build\n```\n",
    )
    doc_zh = GeneratedDocument(
        filename="README.zh-CN.md",
        base_name="README.md",
        language_code="zh-CN",
        content="# 项目名称\n\n<!-- makewiki:section=build -->\n## 构建\n[[id:build]]\n```bash\nmake build\n```\n",
    )

    orchestrator = VerificationOrchestrator(tmp_path)
    report = orchestrator.verify_documents({"en": [doc_en], "zh-CN": [doc_zh]})

    assert len(report.layers) == 6
    assert set(report.layers.keys()) == {"L0", "L1", "L2", "L3", "L4", "L5"}
    # L0/L1 pass on the disk-provable facts; the stable-ID-tagged code block
    # passes the L4a untagged-technical-block check, but the LLM-judged L3/L4b/L5
    # layers (and an empty L2) report pending so the aggregate is never a vacuous
    # pass. (An untagged technical fence would instead fail L4a -> "failed".)
    assert report.layers["L0"].passed
    assert report.layers["L1"].passed
    assert report.verdict == "pending"
    assert report.passed is False
    # No layer may be falsely "passed": the LLM-judged / vacuous L3/L4/L5 layers
    # report pending checks that do not count toward the score, so the aggregate
    # score is honest (below 1.0) rather than inflated to a vacuous 1.0.
    assert report.score < 1.0


def test_orchestrator_verify_single_layer(tmp_path: Path):
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# Title\n\n## Section\nContent",
    )
    orchestrator = VerificationOrchestrator(tmp_path)
    l0_report = orchestrator.verify_layer("L0", {"en": [doc]})

    assert l0_report.layer == "L0"
    assert l0_report.passed


def test_orchestrator_merge_semantic_bundle_adjudicates_llm_layers(tmp_path: Path):
    """A provided SemanticAuditBundle is merged into the report so L3/L4b/L5 are
    authoritative (passed/failed) rather than left pending."""
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# Title\n\n## Build\n```bash\nmake build\n```\n",
    )
    doc_zh = GeneratedDocument(
        filename="README.zh-CN.md",
        base_name="README.md",
        language_code="zh-CN",
        content="# Title\n\n## Build\n```bash\nmake build\n```\n",
    )
    bundle = SemanticAuditBundle(
        documents_digest="sha256:unused",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:1", layer="L3", status="passed",
                rationale_summary="ok",
            ),
            SemanticAuditVerdict(
                review_item_id="L4b:1", layer="L4b", status="failed",
                rationale_summary="prose diverges",
            ),
            SemanticAuditVerdict(
                review_item_id="L5:1", layer="L5", status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    orchestrator = VerificationOrchestrator(tmp_path)
    report = orchestrator.verify_documents(
        {"en": [doc], "zh-CN": [doc_zh]}, semantic_bundle=bundle
    )

    assert report.layers["L3"].passed is True
    assert report.layers["L5"].passed is True
    # L4b failed -> an explicit LLM verdict on the semantic-parity check.
    l4b = [c for c in report.layers["L4"].checks if c.claim_type == "l4b_semantic"]
    assert l4b and l4b[0].status == "failed"

    # Without a bundle, the same L3/L4b/L5 layers stay pending.
    report_no_bundle = orchestrator.verify_documents({"en": [doc], "zh-CN": [doc_zh]})
    assert report_no_bundle.layers["L3"].passed is False
    assert report_no_bundle.layers["L5"].passed is False
    l4b_pending = [
        c for c in report_no_bundle.layers["L4"].checks if c.claim_type == "l4b_semantic"
    ]
    assert l4b_pending and l4b_pending[0].status == "pending"


def test_orchestrator_rejects_model_stale_audit_bundle(tmp_path: Path):
    """A bundle that binds to a STALE semantic model digest is rejected (never
    merged) when the current model digest is supplied, so its outdated LLM
    verdicts cannot mark L3/L4b/L5 passed. This closes the gap where only the
    document digest was enforced at the authoritative merge seam."""
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# Title\n\n## Build\n[[id:build]]\n```bash\nmake build\n```\n",
    )
    doc_zh = GeneratedDocument(
        filename="README.zh-CN.md",
        base_name="README.md",
        language_code="zh-CN",
        content="# Title\n\n## Build\n[[id:build]]\n```bash\nmake build\n```\n",
    )

    # Bundle claims L3 passed but binds to a semantic model digest that is NOT
    # the current one.
    bundle = SemanticAuditBundle(
        documents_digest="sha256:unused",
        semantic_model_digest="sha256:old-model",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:1", layer="L3", status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    orchestrator = VerificationOrchestrator(tmp_path)
    report = orchestrator.verify_documents(
        {"en": [doc], "zh-CN": [doc_zh]},
        semantic_bundle=bundle,
        semantic_model_digest="sha256:current-model",
    )

    # The stale bundle is NOT merged: L3 stays pending, never passed.
    assert report.layers["L3"].passed is False
    assert report.layers["L5"].passed is False

    # A bundle bound to the CURRENT model digest IS merged (L3 passed).
    fresh = SemanticAuditBundle(
        documents_digest="sha256:unused",
        semantic_model_digest="sha256:current-model",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:1", layer="L3", status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    report_fresh = orchestrator.verify_documents(
        {"en": [doc], "zh-CN": [doc_zh]},
        semantic_bundle=fresh,
        semantic_model_digest="sha256:current-model",
    )
    assert report_fresh.layers["L3"].passed is True
