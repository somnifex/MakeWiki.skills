"""Unit tests for VerificationOrchestrator."""

from pathlib import Path

import pytest

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.orchestrator import VerificationOrchestrator
from makewiki_skills.verification.report import LayerReport


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

<!-- makewiki:section=build -->
## Build

[[id:build]]
```bash
make build
```

<!-- makewiki:section=test -->
## Test

[[id:test]]
```bash
make test
```

<!-- makewiki:section=run -->
## Run

[[id:run]]
```bash
myapp run --port 8080
```

<!-- makewiki:section=configure -->
## Configure

Set `server.port` in `./config.yaml`.
"""


def _docs() -> dict[str, list[GeneratedDocument]]:
    """EN + zh-CN writer documents (ID-tagged technical blocks)."""
    zh = _EN.replace("myapp is a tiny scaffold.", "myapp 是一个微型脚手架。")
    return {
        "en": [
            GeneratedDocument(
                filename="README.md",
                base_name="README",
                language_code="en",
                content=_EN,
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="README.zh-CN.md",
                base_name="README",
                language_code="zh-CN",
                content=zh,
            )
        ],
    }


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
    """A provided SemanticAuditBundle is merged ITEM-LEVEL into the report: each
    verdict adjudicates exactly one review item by its real ``review_item_id``.
    Unmentioned pending items STAY pending; the L3/L5 layer verdicts (which
    contain unmentioned items) stay ``pending`` — never ``passed`` — and the gate
    short-circuits to ``pending_semantic_review``, never ``passed``."""
    from makewiki_skills.verification.quality_gate import evaluate_quality_gate
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    proj = _make_project(tmp_path)
    docs = _docs()
    orchestrator = VerificationOrchestrator(proj)

    # Mechanical layers pass; only the LLM-judged L3/L4b/L5 layers are pending.
    base = orchestrator.verify_documents(
        docs, semantic_bundle=SemanticAuditBundle(documents_digest="x", verdicts=[])
    )
    assert base.layers["L0"].verdict == "passed"
    assert base.layers["L1"].verdict == "passed"
    assert base.layers["L2"].verdict == "passed"
    items = list(base.review_items)
    l3_item = next(i for i in items if i.layer == "L3")
    l4b_item = next(i for i in items if i.layer == "L4b")
    l5_item = next(i for i in items if i.layer == "L5")
    assert l3_item is not None and l4b_item is not None and l5_item is not None

    # Adjudicate the L4b item as passed; leave L3 and L5 unmentioned.
    bundle = SemanticAuditBundle(
        documents_digest="x",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l4b_item.review_item_id,
                layer="L4b",
                status="passed",
                rationale_summary="prose parity upheld",
            )
        ],
    )
    report = orchestrator.verify_documents(docs, semantic_bundle=bundle)

    # Item-level: the adjudicated L4b check took the verdict's status.
    l4b_checks = [
        c for c in report.layers["L4"].checks if c.claim_type == "l4b_semantic"
    ]
    assert l4b_checks
    assert l4b_checks[0].status == "passed"

    # The unmentioned pending items STAY pending (not whole-layer-flipped).
    def _check(layer_name, review_item_id):
        for c in report.layers[layer_name].checks:
            if c.review_item_id == review_item_id:
                return c
        return None

    assert _check("L3", l3_item.review_item_id).status == "pending"
    assert _check("L5", l5_item.review_item_id).status == "pending"

    # L3/L5 contain unmentioned items -> their layer verdicts stay pending.
    assert report.layers["L3"].passed is False
    assert report.layers["L3"].verdict == "pending"
    assert report.layers["L5"].passed is False
    assert report.layers["L5"].verdict == "pending"

    # The gate short-circuits to pending_semantic_review; never passed.
    gate = evaluate_quality_gate(report)
    assert gate.verdict == "pending_semantic_review"
    assert gate.passed is False

    # Without a bundle, the same L3/L4b/L5 layers stay pending.
    report_no_bundle = orchestrator.verify_documents(docs)
    assert report_no_bundle.layers["L3"].passed is False
    assert report_no_bundle.layers["L5"].passed is False
    l4b_pending = [
        c
        for c in report_no_bundle.layers["L4"].checks
        if c.claim_type == "l4b_semantic"
    ]
    assert l4b_pending and l4b_pending[0].status == "pending"


def test_orchestrator_rejects_model_stale_audit_bundle(tmp_path: Path):
    """A bundle that binds to a STALE semantic model digest is rejected (never
    merged) when the current model digest is supplied, so its outdated LLM
    verdicts cannot mark L3 passed. Built against REAL review_item_ids so the
    ONLY reason the bundle is not merged is the model-digest staleness.

    Companion honesty case: a bundle that declares a semantic_model_digest but
    receives NO current digest is never silently trusted — it is rejected
    (UNPROVEN) and L3 stays pending."""
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    proj = _make_project(tmp_path)
    docs = _docs()
    orchestrator = VerificationOrchestrator(proj)

    probe = SemanticAuditBundle(documents_digest="x", verdicts=[])
    base = orchestrator.verify_documents(docs, semantic_bundle=probe)
    l3_item = next(i for i in base.review_items if i.layer == "L3")

    # Bundle claims L3 passed but binds to a semantic model digest that is NOT
    # the current one.
    stale = SemanticAuditBundle(
        documents_digest="x",
        semantic_model_digest="sha256:old-model",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l3_item.review_item_id,
                layer="L3",
                status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    report = orchestrator.verify_documents(
        docs, semantic_bundle=stale, semantic_model_digest="sha256:current-model"
    )

    # Stale -> not merged: L3 stays pending, never passed.
    assert report.layers["L3"].passed is False
    assert report.layers["L5"].passed is False

    # Companion: bundle declares a model digest but NO current digest is passed
    # -> the model binding is UNPROVEN -> not silently trusted -> rejected.
    unproven = SemanticAuditBundle(
        documents_digest="x",
        semantic_model_digest="sha256:model-snapshot",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l3_item.review_item_id,
                layer="L3",
                status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    report_unproven = orchestrator.verify_documents(docs, semantic_bundle=unproven)
    assert report_unproven.layers["L3"].passed is False

    # A bundle bound to the CURRENT model digest IS merged (L3 passed).
    fresh = SemanticAuditBundle(
        documents_digest="x",
        semantic_model_digest="sha256:current-model",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l3_item.review_item_id,
                layer="L3",
                status="passed",
                rationale_summary="ok",
            ),
        ],
    )
    report_fresh = orchestrator.verify_documents(
        docs, semantic_bundle=fresh, semantic_model_digest="sha256:current-model"
    )
    assert report_fresh.layers["L3"].passed is True


def test_initial_verify_without_bundle_produces_review_items(tmp_path: Path):
    """REQUIREMENT: a FIRST verify with NO SemanticAuditBundle still computes the
    Review Registry (``report.review_items``) so the pending L3/L4b/L5 semantics
    are exposed for a later audit — the registry is not gated on a bundle."""
    proj = _make_project(tmp_path)
    docs = _docs()
    orchestrator = VerificationOrchestrator(proj)

    report = orchestrator.verify_documents(docs)  # no bundle at all

    assert report.review_items, "first verify must expose review_items"
    layers_present = {ri.layer for ri in report.review_items}
    assert layers_present == {"L3", "L4b", "L5"}
    assert all(ri.status == "pending" for ri in report.review_items)
    # Registry ids are unique and stable (no duplicate, no silent collapse).
    ids = [ri.review_item_id for ri in report.review_items]
    assert len(ids) == len(set(ids))


def test_duplicate_review_item_id_in_registry_is_rejected(tmp_path: Path):
    """REQUIREMENT: a duplicate ``review_item_id`` across pending semantic checks
    must FAIL EXPLICITLY (raise), never silently merge one check over another.

    Two distinct pending checks that resolve to the SAME stable identity would
    otherwise be collapsed by the registry's set/dict lookup — the exact silent
    overwrite the honesty contract forbids."""
    from makewiki_skills.verification.report import VerificationCheck

    proj = _make_project(tmp_path)
    docs = _docs()
    orchestrator = VerificationOrchestrator(proj)

    report = orchestrator.verify_documents(docs)
    # Corrupt the report: two pending L3 checks claiming the same review_item_id.
    report.layers["L3"] = LayerReport(
        layer="L3",
        name="Behavior",
        checks=[
            VerificationCheck(
                layer="L3", target="d.md", claim_type="behavior",
                claim_text="make build", verified=False, status="pending",
                detail="a", review_item_id="L3:d.md:build",
            ),
            VerificationCheck(
                layer="L3", target="d.md", claim_type="behavior",
                claim_text="different claim", verified=False, status="pending",
                detail="b", review_item_id="L3:d.md:build",
            ),
        ],
    )
    report.layers["L5"] = LayerReport(layer="L5", name="Epistemic", checks=[])
    report.layers["L4"] = LayerReport(layer="L4", name="Cross-language", checks=[])

    with pytest.raises(ValueError, match="duplicate review_item_id"):
        orchestrator._build_review_items(report)


def test_partial_audit_keeps_unmentioned_items_pending(tmp_path: Path):
    """REQUIREMENT: items the Auditor did NOT adjudicate STAY pending — a partial
    bundle resolves only what it names, never wholesale-flipping a layer."""
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    proj = _make_project(tmp_path)
    docs = _docs()
    orchestrator = VerificationOrchestrator(proj)

    base = orchestrator.verify_documents(
        docs, semantic_bundle=SemanticAuditBundle(documents_digest="x", verdicts=[])
    )
    l3_item = next(i for i in base.review_items if i.layer == "L3")

    # Adjudicate ONLY the L3 item; L4b and L5 stay unmentioned.
    partial = SemanticAuditBundle(
        documents_digest="x",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l3_item.review_item_id, layer="L3",
                status="passed", rationale_summary="ok",
            )
        ],
    )
    report = orchestrator.verify_documents(docs, semantic_bundle=partial)

    # The unmentioned items keep status pending (not flipped to passed).
    for item in base.review_items:
        if item.review_item_id == l3_item.review_item_id:
            continue
        check = next(
            c for c in report.layers["L4" if item.layer == "L4b" else item.layer].checks
            if c.review_item_id == item.review_item_id
        )
        assert check.status == "pending"
    # The registry represents the full pending set; the gate stays pending.
    from makewiki_skills.verification.quality_gate import evaluate_quality_gate

    gate = evaluate_quality_gate(report)
    assert gate.verdict == "pending_semantic_review"
    assert gate.passed is False
    assert gate.semantic_complete is False


def test_full_audit_transitions_pending_to_passed(tmp_path: Path):
    """REQUIREMENT: a COMPLETE audit (every pending semantic item adjudicated
    passed) transitions the gate from pending to passed: semantic_complete,
    no pending LLM layers, ci_exit_code 0."""
    from makewiki_skills.verification.quality_gate import evaluate_quality_gate
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    proj = _make_project(tmp_path)
    docs = _docs()
    orchestrator = VerificationOrchestrator(proj)

    base = orchestrator.verify_documents(
        docs, semantic_bundle=SemanticAuditBundle(documents_digest="x", verdicts=[])
    )
    full = SemanticAuditBundle(
        documents_digest="x",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=item.review_item_id, layer=item.layer,
                status="passed", rationale_summary="ok",
            )
            for item in base.review_items
        ],
    )
    report = orchestrator.verify_documents(docs, semantic_bundle=full)
    gate = evaluate_quality_gate(report)
    # Pending -> passed transition is complete and honest.
    assert gate.semantic_complete is True
    assert gate.pending_llm_layers == []
    assert gate.verdict == "passed"
    assert gate.passed is True
    assert gate.ci_exit_code == 0

