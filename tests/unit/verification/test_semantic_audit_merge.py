"""Item-level semantic-bundle merge regression tests (§11 of the spec).

These tests pin the NEW item-level merge semantics of
``VerificationOrchestrator.verify_documents(..., semantic_bundle=...)``:

* Each bundle verdict adjudicates EXACTLY ONE review item by its stable
  ``review_item_id`` (never a whole layer).
* Unmentioned pending items STAY pending; a layer with any unmentioned item
  stays ``pending``.
* A verdict for an UNKNOWN ``review_item_id`` (matching no pending semantic
  check) REJECTS the whole bundle — nothing merged, L3/L4b/L5 stay pending.
* A bundle declaring a ``semantic_model_digest`` is merged ONLY when a current
  digest is supplied AND equals it; a declared digest with no current digest is
  NOT silently trusted (rejected), and a mismatch is REJECTED (stale).
* A merged check records ``verification_source == "semantic_audit_bundle"`` and
  carries the Auditor's provenance (auditor / rationale / confidence / evidence).

The ``review_items`` registry is a stable pre-bundle manifest; item-level
adjudication is asserted on the actual LayerReport checks (status fields).
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.orchestrator import VerificationOrchestrator
from makewiki_skills.verification.quality_gate import evaluate_quality_gate
from makewiki_skills.verification.report import LayerReport, VerificationCheck
from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    SemanticAuditVerdict,
)


def _make_project(tmp_path: Path) -> Path:
    """A tiny repo with a real CLI so the mechanical layers (L0/L1/L2/L4a) pass,
    leaving only the LLM-judged L3/L4b/L5 layers pending."""
    proj = tmp_path / "project"
    proj.mkdir(exist_ok=True)
    (proj / "Makefile").write_text(
        """.PHONY: build test
build:
\tgcc -o app main.c
test:
\tmake -q
""",
        encoding="utf-8",
    )
    (proj / "config.yaml").write_text("server:\n  port: 8080\n", encoding="utf-8")
    (proj / "pyproject.toml").write_text(
        '[project]\nname="myapp"\nversion="1.0.0"\n'
        '[project.scripts]\nmyapp="cli:main"\n',
        encoding="utf-8",
    )
    (proj / "cli.py").write_text(
        'import typer\napp=typer.Typer()\n'
        '@app.command()\ndef run(port:int=8080, host:str="0.0.0.0"):\n    print(port)\n'
        '@app.command()\ndef serve():\n    print("s")\n'
        'def main():\n    app()\n',
        encoding="utf-8",
    )
    (proj / "README.md").write_text("# myapp\n\nmyapp is a tiny app.\n")
    return proj


_EN = """# myapp

myapp is a tiny scaffold.

## Build

[[id:build]]
```bash
make build
```

## Test

[[id:test]]
```bash
make test
```

## Run

[[id:run]]
```bash
myapp run --port 8080
```

## Configure

Set `server.port` in `./config.yaml`.
"""


def _docs() -> dict[str, list[GeneratedDocument]]:
    """EN + zh-CN writer documents (ID-tagged technical blocks)."""
    zh = _EN.replace("myapp is a tiny scaffold.", "myapp 是一个微型脚手架。")
    en = GeneratedDocument(
        filename="README.md",
        base_name="README",
        language_code="en",
        content=_EN,
    )
    zhdoc = GeneratedDocument(
        filename="README.zh-CN.md",
        base_name="README",
        language_code="zh-CN",
        content=zh,
    )
    return {"en": [en], "zh-CN": [zhdoc]}


def _orchestrator(tmp_path: Path) -> VerificationOrchestrator:
    return VerificationOrchestrator(_make_project(tmp_path))


def _pending_review_items(
    tmp_path: Path, docs: dict[str, list[GeneratedDocument]]
) -> list:
    """Run mechanical verification with an empty-verdict probe so Python computes
    the authoritative registry of pending semantic review items (real ids)."""
    orchestrator = _orchestrator(tmp_path)
    probe = SemanticAuditBundle(documents_digest="sha256:probe", verdicts=[])
    report = orchestrator.verify_documents(docs, semantic_bundle=probe)
    return list(report.review_items)


def _find_check(report, review_item_id: str):
    for layer_name, lr in report.layers.items():
        if layer_name not in ("L3", "L4", "L5"):
            continue
        for check in lr.checks:
            if check.review_item_id == review_item_id:
                return check
    return None


# ---------------------------------------------------------------------------
# Item-level merge semantics
# ---------------------------------------------------------------------------


def test_partial_semantic_bundle_keeps_unmentioned_items_pending(tmp_path: Path):
    """A bundle that adjudicates only SOME review items leaves the others pending,
    and a layer containing any unmentioned item stays ``pending`` (never passes)."""
    docs = _docs()
    items = _pending_review_items(tmp_path, docs)
    assert len(items) >= 3  # at least one L3, one L4b, and two L5 items

    # Adjudicate ONE item: the L4b prose-parity item, as passed. Leave the L3
    # and L5 items unmentioned so those layers must stay pending.
    l4b_item = next(i for i in items if i.layer == "L4b")
    bundle = SemanticAuditBundle(
        documents_digest="sha256:x",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l4b_item.review_item_id,
                layer="L4b",
                status="passed",
                rationale_summary="prose parity upheld",
            )
        ],
    )
    orchestrator = _orchestrator(tmp_path)
    report = orchestrator.verify_documents(docs, semantic_bundle=bundle)

    # Item-level: the adjudicated L4b check resolved; the L3/L5 items did not.
    assert _find_check(report, l4b_item.review_item_id).status == "passed"
    for item in items:
        if item.review_item_id != l4b_item.review_item_id:
            assert _find_check(report, item.review_item_id).status == "pending", (
                f"unmentioned item {item.review_item_id!r} must stay pending"
            )

    # A layer containing any unmentioned item stays pending (not passed).
    assert report.layers["L3"].verdict == "pending"
    assert report.layers["L5"].verdict == "pending"

    # The gate short-circuits to pending_semantic_review; never passed.
    gate = evaluate_quality_gate(report)
    assert gate.verdict == "pending_semantic_review"
    assert gate.passed is False
    assert gate.semantic_complete is False


def test_complete_semantic_bundle_resolves_all_expected_items(tmp_path: Path):
    """A bundle adjudicating EVERY pending semantic review item resolves them all
    and drives the semantic layers to passed."""
    docs = _docs()
    items = _pending_review_items(tmp_path, docs)
    assert items  # there are real expected items

    bundle = SemanticAuditBundle(
        documents_digest="sha256:x",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=item.review_item_id,
                layer=item.layer,
                status="passed",
                rationale_summary="adjudicated OK",
            )
            for item in items
        ],
    )
    orchestrator = _orchestrator(tmp_path)
    report = orchestrator.verify_documents(docs, semantic_bundle=bundle)

    # Every expected item's check was adjudicated (passed).
    for item in items:
        check = _find_check(report, item.review_item_id)
        assert check is not None
        assert check.status == "passed"

    # No pending semantic checks remain -> gate is semantically complete.
    remaining = [
        c
        for layer_name, lr in report.layers.items()
        if layer_name in ("L3", "L4", "L5")
        for c in lr.checks
        if c.review_item_id and c.status == "pending"
    ]
    assert remaining == []
    gate = evaluate_quality_gate(report)
    assert gate.semantic_complete is True
    assert gate.pending_llm_layers == []


def test_unknown_review_item_id_is_rejected(tmp_path: Path):
    """A verdict whose review_item_id matches NO pending semantic check rejects
    the WHOLE bundle: nothing merged, L3/L4b/L5 stay pending."""
    docs = _docs()
    items = _pending_review_items(tmp_path, docs)
    orchestrator = _orchestrator(tmp_path)

    bundle = SemanticAuditBundle(
        documents_digest="sha256:x",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=items[0].review_item_id,
                layer=items[0].layer,
                status="passed",
                rationale_summary="ok",
            ),
            SemanticAuditVerdict(
                review_item_id="L3:1",  # fake id: matches no real pending check
                layer="L3",
                status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    report = orchestrator.verify_documents(docs, semantic_bundle=bundle)

    # The whole bundle is rejected — even the veridical verdict is not merged.
    assert report.details.get("semantic_bundle_rejected") is True
    assert report.details.get("semantic_bundle_rejection_reason") == "unknown_review_item_id"
    for layer in ("L3", "L4", "L5"):
        assert report.layers[layer].verdict == "pending"


def test_semantic_audit_provenance_is_preserved(tmp_path: Path):
    """A merged check carries verification_source == 'semantic_audit_bundle' and
    its detail mentions the auditor, rationale, confidence, and evidence."""
    docs = _docs()
    items = _pending_review_items(tmp_path, docs)
    bundle = SemanticAuditBundle(
        documents_digest="sha256:x",
        auditor="fake_primary_auditor",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=items[0].review_item_id,
                layer=items[0].layer,
                status="passed",
                rationale_summary="behavior matches traced source",
                evidence_refs=["src/app/cli.py:120-148"],
                confidence="high",
            )
        ],
    )
    orchestrator = _orchestrator(tmp_path)
    report = orchestrator.verify_documents(docs, semantic_bundle=bundle)

    check = _find_check(report, items[0].review_item_id)
    assert check.verification_source == "semantic_audit_bundle"
    assert "fake_primary_auditor" in check.detail
    assert "behavior matches traced source" in check.detail  # rationale
    assert "high" in check.detail  # confidence
    assert "src/app/cli.py:120-148" in check.detail  # evidence
    # The stable identity is preserved on the merged check.
    assert check.review_item_id == items[0].review_item_id


# ---------------------------------------------------------------------------
# Semantic-model digest binding
# ---------------------------------------------------------------------------


def test_stale_semantic_model_digest_is_rejected(tmp_path: Path):
    """A bundle bound to a STALE semantic model digest is rejected (never merged)
    when the current digest is supplied — L3 stays pending."""
    docs = _docs()
    items = _pending_review_items(tmp_path, docs)
    l3_item = next(i for i in items if i.layer == "L3")

    bundle = SemanticAuditBundle(
        documents_digest="sha256:x",
        semantic_model_digest="sha256:old-model",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l3_item.review_item_id,
                layer="L3",
                status="passed",
                rationale_summary="ok",
            )
        ],
    )
    orchestrator = _orchestrator(tmp_path)
    report = orchestrator.verify_documents(
        docs, semantic_bundle=bundle, semantic_model_digest="sha256:current-model"
    )
    # Rejected on staleness -> the L3 item is never adjudicated.
    assert report.layers["L3"].verdict == "pending"
    assert _find_check(report, l3_item.review_item_id).status == "pending"


def test_bundle_model_digest_without_current_model_is_not_silently_trusted(
    tmp_path: Path,
):
    """A bundle that declares a semantic_model_digest but receives NO current
    digest cannot be proven fresh -> it is rejected (UNPROVEN), never silently
    trusted, so L3 stays pending."""
    docs = _docs()
    items = _pending_review_items(tmp_path, docs)
    l3_item = next(i for i in items if i.layer == "L3")

    bundle = SemanticAuditBundle(
        documents_digest="sha256:x",
        semantic_model_digest="sha256:model-snapshot",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l3_item.review_item_id,
                layer="L3",
                status="passed",
                rationale_summary="ok",
            )
        ],
    )
    orchestrator = _orchestrator(tmp_path)
    # No semantic_model_digest argument supplied -> binding UNPROVEN -> reject.
    report = orchestrator.verify_documents(docs, semantic_bundle=bundle)
    assert report.layers["L3"].verdict == "pending"
    assert _find_check(report, l3_item.review_item_id).status == "pending"


# ---------------------------------------------------------------------------
# LayerReport subset accessors
# ---------------------------------------------------------------------------


def test_failures_only_returns_failed_checks():
    """`failures()` returns ONLY status==failed checks; pending/unknown/warning/
    not_applicable are reported by their own accessors, never as failures."""
    checks = []
    for status, claim_text in [
        ("failed", "contradicted"),
        ("pending", "unproven"),
        ("unknown", "insufficient"),
        ("warning", "advisory"),
        ("not_applicable", "n/a"),
        ("passed", "proven"),
    ]:
        checks.append(
            VerificationCheck(
                layer="L2",
                target="d.md",
                claim_type="structure",
                claim_text=claim_text,
                verified=(status == "passed"),
                status=status,
                detail="detail",
            )
        )
    lr = LayerReport(layer="L2", name="Interface", checks=checks)

    assert [c.status for c in lr.failures()] == ["failed"]
    assert [c.claim_text for c in lr.failures()] == ["contradicted"]

    assert [c.status for c in lr.pending()] == ["pending"]
    assert [c.status for c in lr.unknowns()] == ["unknown"]
    assert [c.status for c in lr.warnings()] == ["warning"]
    assert [c.status for c in lr.not_applicable()] == ["not_applicable"]

    # None of the non-failed subsets leak into failures().
    failing_ids = {c.check_id for c in lr.failures()}
    non_failed = lr.pending() + lr.unknowns() + lr.warnings() + lr.not_applicable()
    for c in non_failed:
        assert c.check_id not in failing_ids
