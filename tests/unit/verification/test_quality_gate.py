"""Tests for the unified Quality Gate and L0-L5 orchestrator wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.verification.orchestrator import VerificationOrchestrator
from makewiki_skills.verification.quality_gate import (
    QualityGateResult,
    evaluate_quality_gate,
)
from makewiki_skills.verification.report import (
    ComprehensiveVerificationReport,
    LayerReport,
    VerificationCheck,
)


def _make_report() -> ComprehensiveVerificationReport:
    """A clean report where every layer passes with at least one check."""
    layers: dict[str, LayerReport] = {}
    for name, label in [
        ("L0", "Syntax & Structure"),
        ("L1", "Existence"),
        ("L2", "Interface"),
        ("L3", "Behavior"),
        ("L4", "Cross-language"),
        ("L5", "Epistemic"),
    ]:
        layers[name] = LayerReport(
            layer=name,
            name=label,
            checks=[
                VerificationCheck(
                    layer=name,
                    target="doc.md",
                    claim_type="structure",
                    claim_text="x",
                    verified=True,
                    status="passed",
                    detail="ok",
                )
            ],
        )
    return ComprehensiveVerificationReport(layers=layers)


def _layer_with_failure(layer: str, name: str, label: str) -> LayerReport:
    return LayerReport(
        layer=layer,
        name=name,
        checks=[
            VerificationCheck(
                layer=layer,
                target="doc.md",
                claim_type="structure",
                claim_text="x",
                verified=False,
                status="failed",
                detail="boom",
            )
        ],
    )


def test_gate_passes_when_all_mechanical_layers_pass():
    report = _make_report()
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert isinstance(result, QualityGateResult)
    assert result.passed is True
    assert result.exit_code == 0
    assert result.grounding_score == pytest.approx(1.0)


def test_gate_fails_on_mechanical_layer_failure():
    report = _make_report()
    report.layers["L1"] = _layer_with_failure("L1", "Existence", "x")
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.passed is False
    assert result.exit_code == 1
    assert result.existence_passed is False


def test_gate_fails_below_grounding_threshold():
    report = _make_report()
    report.layers["L1"] = _layer_with_failure("L1", "Existence", "x")
    # Three failing layers drag the score below 1.0; gate must fail.
    report.layers["L2"] = _layer_with_failure("L2", "Interface", "x")
    report.layers["L0"] = _layer_with_failure("L0", "Syntax & Structure", "x")
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.grounding_score < 1.0
    assert result.passed is False


def test_pending_layer_does_not_fail_gate_by_default():
    report = _make_report()
    # Empty/pending L3 (LLM-judged) should not fail the gate when allow_pending.
    report.layers["L3"] = LayerReport(layer="L3", name="Behavior", checks=[])
    cfg = MakeWikiConfig.default(Path("."))
    cfg.quality.allow_pending_llm_layers = True
    cfg.quality.fail_on_critical = False
    result = evaluate_quality_gate(report, cfg, fail_on_critical=cfg.quality.fail_on_critical)
    # Pending LLM (no audit verdict) with allow_pending=True -> pending_semantic_review.
    # exit-policy code 0, but NEVER passed: pending is never passed.
    assert result.verdict == "pending_semantic_review"
    assert result.passed is False
    assert result.ci_exit_code == 0
    assert result.exit_code == 0


def test_llm_layer_passed_flags_reflect_actual_layer_status():
    """L3/L4/L5 passed flags must mirror the real per-layer verdict.

    Regression guard: these fields were once ``bool == "passed"`` which made
    them always False regardless of the layer actually passing.
    """
    report = _make_report()
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.behavior_passed is True
    assert result.cross_language_passed is True
    assert result.epistemic_passed is True

    # A failed LLM-judged layer drives its own flag False.
    report.layers["L3"] = _layer_with_failure("L3", "Behavior", "x")
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.behavior_passed is False
    assert result.cross_language_passed is True
    assert result.epistemic_passed is True


def test_orchestrator_runs_all_layers_on_directory():
    """verify-docs path: orchestrator produces L0-L5 on a real wiki directory."""
    from makewiki_skills.generator.language_generator import GeneratedDocument

    project_dir = Path(__file__).resolve().parents[3]  # repo root
    documents: dict[str, list[GeneratedDocument]] = {
        "en": [
            GeneratedDocument(
                filename="README.md",
                base_name="README",
                language_code="en",
                content=project_dir.joinpath("README.md").read_text(encoding="utf-8"),
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="README.zh-CN.md",
                base_name="README",
                language_code="zh-CN",
                content=project_dir.joinpath("README.en.md").read_text(encoding="utf-8"),
            )
        ],
    }
    orchestrator = VerificationOrchestrator(project_dir)
    report = orchestrator.verify_documents(documents, wiki_dir=project_dir)
    assert set(report.layers.keys()) == {"L0", "L1", "L2", "L3", "L4", "L5"}
    assert report.total_checks > 0


# ---------------------------------------------------------------------------
# Honesty model: verdict / mechanical vs semantic scores
# ---------------------------------------------------------------------------


def _review_report(mech_passed: bool = True, llm_pending: bool = True) -> ComprehensiveVerificationReport:
    """A report with clean mechanical layers, optionally pending LLM layers."""
    layers: dict[str, LayerReport] = {}
    for name in ("L0", "L1", "L2"):
        layers[name] = LayerReport(
            layer=name,
            name=name,
            checks=[
                VerificationCheck(
                    layer=name, target="d.md", claim_type="structure",
                    claim_text="x", verified=True, status="passed", detail="ok",
                )
            ],
        )
    for name in ("L3", "L4", "L5"):
        if llm_pending:
            layers[name] = LayerReport(
                layer=name,
                name=name,
                checks=[
                    VerificationCheck(
                        layer=name, target="d.md", claim_type="l4b_semantic" if name == "L4" else "behavior",
                        claim_text="semantic", verified=False, status="pending", detail="LLM pending",
                    )
                ],
            )
        else:
            layers[name] = LayerReport(
                layer=name,
                name=name,
                checks=[
                    VerificationCheck(
                        layer=name, target="d.md", claim_type="structure",
                        claim_text="y", verified=True, status="passed", detail="ok",
                    )
                ],
            )
    return ComprehensiveVerificationReport(layers=layers)


def test_quality_gate_pending_semantic_review():
    """Pending L3/L4b/L5 yields verdict=pending_semantic_review, honest but non-failing.

    The exit-policy CI code is 0 (allow_pending=True grants the exit policy), but
    the gate is NEVER ``passed`` — ``passed == (verdict == "passed")`` strictly,
    so a pending gate is never reported as passed (audit finding #1).
    """
    report = _review_report(llm_pending=True)
    cfg = MakeWikiConfig.default(Path("."))
    cfg.quality.allow_pending_llm_layers = True
    result = evaluate_quality_gate(report, cfg)

    assert result.mechanical_passed is True
    assert result.verdict == "pending_semantic_review"
    assert result.semantic_complete is False
    assert set(result.pending_llm_layers) == {"L3", "L4b", "L5"}
    # Honesty contract: pending semantic review is NEVER passed.
    assert result.passed is False
    # Exit policy: pending semantic review exits 0 while allowed.
    assert result.ci_exit_code == 0
    assert result.exit_code == 0


def test_quality_gate_verdict_failed_on_mechanical_failure():
    """A failed mechanical layer forces verdict=failed and exit 1."""
    report = _review_report(llm_pending=True)
    report.layers["L1"] = LayerReport(
        layer="L1", name="Existence",
        checks=[
            VerificationCheck(
                layer="L1", target="missing.md", claim_type="path",
                claim_text="missing.md", verified=False, status="failed", detail="not on disk",
            )
        ],
    )
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.verdict == "failed"
    assert result.passed is False
    assert result.exit_code == 1


def test_quality_gate_mechanical_score_excludes_pending_llm():
    """Pending LLM layers must not pull down mechanical_score."""
    report = _review_report(llm_pending=True)
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.mechanical_score == pytest.approx(1.0)
    assert result.grounding_score < result.mechanical_score  # overall includes pending


def test_quality_gate_semantic_score_none_when_pending():
    report = _review_report(llm_pending=True)
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.semantic_score is None


def test_quality_gate_all_adjudicated_passes():
    """Every layer adjudicated (no pending) and non-blocking -> passed + complete."""
    report = _review_report(llm_pending=False)
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.verdict == "passed"
    assert result.semantic_complete is True
    assert result.pending_llm_layers == []
    assert result.semantic_score == pytest.approx(1.0)
    assert result.passed is True
    assert result.exit_code == 0


def test_quality_gate_verdict_failed_on_explicit_llm_failure():
    """An explicitly-failed LLM-judged layer fails the gate (never passed/exit 0).

    Regression guard: the verdict branch once ignored ``llm_failed`` entirely, so
    an L3/L5 check that explicitly failed was absorbed and reported as
    ``passed=True``/exit 0 when other layers were clean — contradicting the
    module's own "unless their checks explicitly failed" contract.
    """
    # Clean mechanical + clean L4/L5, but an L3 check explicitly FAILED.
    report = _review_report(llm_pending=False)
    report.layers["L3"] = LayerReport(
        layer="L3", name="Behavior",
        checks=[
            VerificationCheck(
                layer="L3", target="d.md", claim_type="behavior",
                claim_text="the CLI returns 0 on success", verified=False,
                status="failed", detail="contradicts traced source",
            )
        ],
    )
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.verdict == "failed"
    assert result.passed is False
    assert result.exit_code == 1
    assert result.unresolved_major == 1


def test_quality_gate_pending_mechanical_layer_never_reports_passed():
    """An un-proven (empty/pending) mechanical layer withholds a clean PASS.

    Regression guard: the verdict once ignored pending MECHANICAL layers, so an
    empty L1/L2 (→ pending) combined with fully-adjudicated LLM layers produced
    ``verdict="passed"`` while ``passed``/exit_code disagreed. A pending
    mechanical layer must never yield a vacuous ``passed`` verdict — and, per
    audit finding #4, it is reported as its own verdict
    ``pending_mechanical_verification`` (ci_exit_code 3), distinct from the
    LLM-pending state.
    """
    report = _review_report(llm_pending=False)
    # Empty L2 (no interface facts extracted) -> LayerReport with no checks -> pending.
    report.layers["L2"] = LayerReport(layer="L2", name="Interface", checks=[])
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.verdict != "passed"  # honest: interface not proven
    assert result.interface_passed is False
    assert result.passed is False
    assert result.verdict == "pending_mechanical_verification"
    assert result.pending_mechanical_layers == ["L2"]
    assert result.ci_exit_code == 3
    assert result.exit_code == 3
    assert result.semantic_complete is True  # nothing pending on the LLM side


# ---------------------------------------------------------------------------
# CAI / audit-fix regressions: honesty contract, ci_exit_code mapping,
# allow_pending_llm_layers flip, semantic bundle merge, CLI rendering.
# ---------------------------------------------------------------------------


def test_pending_semantic_review_never_has_passed_true():
    """CRITICAL regression: ``passed == (verdict == "passed")`` STRICTLY.

    A pending gate must NEVER yield ``passed=True`` — previously a mechanically-
    clean report with pending LLM layers reported ``passed=True`` while the
    verdict read ``pending_semantic_review``. That decoupling is removed.
    """
    for allow_pending in (True, False):
        report = _review_report(llm_pending=True)
        result = evaluate_quality_gate(
            report,
            MakeWikiConfig.default(Path(".")),
            allow_pending_llm_layers=allow_pending,
        )
        assert result.passed is False
        assert result.passed == (result.verdict == "passed")


def test_allow_pending_llm_layers_false_forces_pending_to_failed():
    """MAJOR: allow_pending_llm_layers actually changes the verdict.

    When False, a pending LLM layer (L3/L4b/L5) with no audit verdict is NOT
    allowed — the gate verdict flips to ``failed`` and Python exits 1.
    """
    report = _review_report(llm_pending=True)
    # Mechanical layers clean, only LLM layers pending -> with the flag False,
    # pending-with-no-bundle is not allowed.
    cfg = MakeWikiConfig.default(Path("."))
    cfg.quality.allow_pending_llm_layers = False
    result = evaluate_quality_gate(report, cfg)
    assert result.verdict == "failed"
    assert result.passed is False
    assert result.ci_exit_code == 1
    assert result.exit_code == 1

    # The same report with the flag True stays pending (exit-policy 0).
    cfg2 = MakeWikiConfig.default(Path("."))
    cfg2.quality.allow_pending_llm_layers = True
    result2 = evaluate_quality_gate(report, cfg2)
    assert result2.verdict == "pending_semantic_review"
    assert result2.ci_exit_code == 0
    assert result2.passed is False


def test_ci_exit_code_mapping_all_four_branches():
    """SPEC: ci_exit_code maps passed->0, failed->1, pending_semantic->0-or-2,
    pending_mechanical->3 (the honest base for pending_semantic is 2)."""
    from makewiki_skills.verification.quality_gate import ci_exit_code_for

    assert ci_exit_code_for("passed") == 0
    assert ci_exit_code_for("failed") == 1
    # Base honest mapping for pending_semantic_review is 2; the default
    # allow_pending exit policy overrides it to 0.
    assert ci_exit_code_for("pending_semantic_review", allow_pending_llm_layers=False) == 2
    assert ci_exit_code_for("pending_semantic_review", allow_pending_llm_layers=True) == 0
    assert ci_exit_code_for("pending_mechanical_verification") == 3

    # End-to-end: each reachable verdict surfaces the right process exit code.
    passed = evaluate_quality_gate(
        _review_report(llm_pending=False), MakeWikiConfig.default(Path("."))
    )
    assert passed.verdict == "passed"
    assert passed.ci_exit_code == 0

    _failed_report = _review_report(llm_pending=False)
    _failed_report.layers["L1"] = _layer_with_failure("L1", "Existence", "x")
    failed = evaluate_quality_gate(_failed_report, MakeWikiConfig.default(Path(".")))
    assert failed.verdict == "failed"
    assert failed.ci_exit_code == 1


def test_quality_gate_separates_l4a_mechanical_and_l4b_semantic():
    """REPORT: L4a (mechanical parity) and L4b (semantic prose parity) are
    distinct states in the honest pipeline, not one conflated L4 layer.

    A failed L4b (semantic) check is an LLM failure; a pending L4a (mechanical)
    check is a mechanical pending that withholds PASS and reports
    pending_mechanical_verification.
    """
    from makewiki_skills.verification.report import VerificationCheck

    # Mechanical layers clean + L4a pending (one pending mechanical check) and
    # L4b cleanly passed, L3/L5 passed -> pending_mechanical_verification.
    report = _review_report(llm_pending=False)
    report.layers["L4"] = LayerReport(
        layer="L4",
        name="Cross-language",
        checks=[
            VerificationCheck(
                layer="L4", target="d.md", claim_type="l4a_mechanical",
                claim_text="block parity", verified=False, status="pending",
                detail="mechanical parity not yet proven",
            ),
            VerificationCheck(
                layer="L4", target="d.md", claim_type="l4b_semantic",
                claim_text="prose parity", verified=True, status="passed",
                detail="adjudicated",
            ),
        ],
    )
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.l4a_status == "pending"
    assert result.l4b_status == "passed"
    assert result.verdict == "pending_mechanical_verification"
    assert result.ci_exit_code == 3
    assert result.passed is False

    # Now L4a passes but L4b fails -> an explicit LLM (semantic) failure -> failed.
    report2 = _review_report(llm_pending=False)
    report2.layers["L4"] = LayerReport(
        layer="L4",
        name="Cross-language",
        checks=[
            VerificationCheck(
                layer="L4", target="d.md", claim_type="l4a_mechanical",
                claim_text="block parity", verified=True, status="passed",
                detail="ok",
            ),
            VerificationCheck(
                layer="L4", target="d.md", claim_type="l4b_semantic",
                claim_text="prose parity", verified=False, status="failed",
                detail="LLM did not uphold prose parity",
            ),
        ],
    )
    result2 = evaluate_quality_gate(report2, MakeWikiConfig.default(Path(".")))
    assert result2.l4a_status == "passed"
    assert result2.l4b_status == "failed"
    assert result2.verdict == "failed"
    assert result2.ci_exit_code == 1


# --- Orchestrator + semantic bundle merge (findings 7/9) ---------------------


def _audit_bundle(verdicts):
    from makewiki_skills.verification.semantic_audit import SemanticAuditBundle

    return SemanticAuditBundle(
        documents_digest="sha256:unused",
        verdicts=verdicts,
    )


def _project_and_docs(tmp_path: Path):
    """A tiny repo (real CLI) + EN/zh-CN writer docs so the mechanical layers
    pass and only the LLM-judged L3/L4b/L5 layers stay pending."""
    from makewiki_skills.generator.language_generator import GeneratedDocument

    proj = tmp_path / "project"
    proj.mkdir(exist_ok=True)
    (proj / "Makefile").write_text(
        ".PHONY: build test\nbuild:\n\tgcc -o app main.c\ntest:\n\tmake -q\n"
    )
    (proj / "config.yaml").write_text("server:\n  port: 8080\n")
    (proj / "pyproject.toml").write_text(
        '[project]\nname="myapp"\nversion="1.0.0"\n'
        '[project.scripts]\nmyapp="cli:main"\n'
    )
    (proj / "cli.py").write_text(
        'import typer\napp=typer.Typer()\n'
        '@app.command()\ndef run(port:int=8080, host:str="0.0.0.0"):\n    print(port)\n'
        '@app.command()\ndef serve():\n    print("s")\n'
        'def main():\n    app()\n'
    )
    (proj / "README.md").write_text("# myapp\n\nmyapp is a tiny app.\n")

    en = """# myapp

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
    zh = en.replace("myapp is a tiny scaffold.", "myapp 是一个微型脚手架。")
    docs: dict[str, list] = {
        "en": [
            GeneratedDocument(
                filename="README.md", base_name="README", language_code="en", content=en
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
    return proj, docs


def test_orchestrator_merges_semantic_bundle_verdicts(tmp_path: Path):
    """An LLM audit bundle adjudicating EVERY pending semantic review item makes
    L3/L4b/L5 authoritative instead of pending -> semantic_complete and no
    pending LLM layers. Item-level: the bundle's ids are the REAL review_item_ids
    Python computed."""
    from makewiki_skills.verification.orchestrator import VerificationOrchestrator
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    proj, docs = _project_and_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)

    # Mechanical verify with an empty-verdict probe to compute the REAL registry.
    probe = SemanticAuditBundle(documents_digest="sha256:unused", verdicts=[])
    base = orchestrator.verify_documents(docs, wiki_dir=proj, semantic_bundle=probe)
    assert base.review_items  # Python actually computed expected semantic items
    assert base.layers["L3"].verdict == "pending"

    # A COMPLETE bundle: every pending semantic item adjudicated as passed.
    bundle = SemanticAuditBundle(
        documents_digest="sha256:unused",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=item.review_item_id,
                layer=item.layer,
                status="passed",
                rationale_summary="ok",
            )
            for item in base.review_items
        ],
    )
    report = orchestrator.verify_documents(
        docs, wiki_dir=proj, semantic_bundle=bundle
    )
    # The merged layers are adjudicated (passed), not pending.
    assert report.layers["L3"].passed is True
    assert report.layers["L5"].passed is True
    l4b_checks = [
        c for c in report.layers["L4"].checks if c.claim_type == "l4b_semantic"
    ]
    assert l4b_checks and l4b_checks[0].status == "passed"
    gate = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    # EVERY pending semantic item was adjudicated -> semantically complete.
    assert gate.semantic_complete is True
    assert gate.pending_llm_layers == []


def test_orchestrator_partial_semantic_bundle_keeps_gate_pending(tmp_path: Path):
    """A PARTIAL bundle (only SOME review items adjudicated) keeps the gate at
    pending_semantic_review: the remaining items stay pending and the layers that
    still contain an unmentioned item are not passed."""
    from makewiki_skills.verification.orchestrator import VerificationOrchestrator
    from makewiki_skills.verification.semantic_audit import (
        SemanticAuditBundle,
        SemanticAuditVerdict,
    )

    proj, docs = _project_and_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)

    probe = SemanticAuditBundle(documents_digest="sha256:unused", verdicts=[])
    base = orchestrator.verify_documents(docs, wiki_dir=proj, semantic_bundle=probe)
    l4b_item = next(i for i in base.review_items if i.layer == "L4b")

    # Adjudicate ONLY the L4b item; leave L3 and L5 unmentioned.
    partial = SemanticAuditBundle(
        documents_digest="sha256:unused",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id=l4b_item.review_item_id,
                layer="L4b",
                status="passed",
                rationale_summary="ok",
            )
        ],
    )
    report = orchestrator.verify_documents(
        docs, wiki_dir=proj, semantic_bundle=partial
    )
    gate = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert gate.verdict == "pending_semantic_review"
    assert gate.passed is False
    assert gate.semantic_complete is False
    # The unmentioned semantic layers remain pending, so they are not LLM-resolved.
    assert set(gate.pending_llm_layers) >= {"L3", "L5"}
    assert report.layers["L5"].verdict == "pending"


def test_orchestrator_stale_or_absent_bundle_leaves_semantic_layers_pending(
    tmp_path: Path,
):
    """Absent bundle (no --semantic-audit) leaves L3/L4b/L5 pending and the gate
    NOT passed. A bundle that mentions only SOME of the semantic layers also
    leaves the unmentioned layers pending (layers untouched stay pending)."""
    from makewiki_skills.verification.orchestrator import VerificationOrchestrator

    proj, docs = _project_and_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)

    # No bundle -> L3/L4b/L5 stay pending -> gate is NOT passed (honest).
    report = orchestrator.verify_documents(docs, wiki_dir=proj)
    gate = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert "L3" in gate.pending_llm_layers
    assert "L4b" in gate.pending_llm_layers
    assert "L5" in gate.pending_llm_layers
    assert gate.passed is False

    # A bundle that adjudicates the real L3 item resolves L3, leaving L4b/L5
    # (whose real pending items are unmentioned) pending.
    probe = orchestrator.verify_documents(
        docs,
        wiki_dir=proj,
        semantic_bundle=_audit_bundle([]),
    )
    l3_item = next(i for i in probe.review_items if i.layer == "L3")
    report2 = orchestrator.verify_documents(
        docs,
        wiki_dir=proj,
        semantic_bundle=_audit_bundle(
            [
                {
                    "review_item_id": l3_item.review_item_id,
                    "layer": "L3",
                    "status": "passed",
                    "rationale_summary": "ok",
                }
            ]
        ),
    )
    gate2 = evaluate_quality_gate(report2, MakeWikiConfig.default(Path(".")))
    assert "L3" not in gate2.pending_llm_layers
    assert "L4b" in gate2.pending_llm_layers  # untouched by the bundle
    assert "L5" in gate2.pending_llm_layers
    assert gate2.passed is False


def test_reverify_does_not_reset_valid_llm_verdict_to_pending():
    """Re-verify contract: once a semantic layer carries an audit-bundle verdict
    in the report, the gate must NOT reset it back to pending. The gate reads the
    report faithfully — merged passed/failed semantic layers stay adjudicated."""
    from makewiki_skills.verification.report import VerificationCheck

    # Clean mechanical layers (L0/L1/L2 passed, empty L4a not applicable) with
    # ADJUDICATED semantic layers (L3/L4b/L5 passed from an audit bundle).
    layers: dict[str, LayerReport] = {}
    for name in ("L0", "L1", "L2"):
        layers[name] = LayerReport(
            layer=name, name=name,
            checks=[VerificationCheck(
                layer=name, target="d.md", claim_type="structure",
                claim_text="x", verified=True, status="passed", detail="ok",
            )],
        )
    layers["L3"] = LayerReport(
        layer="L3", name="Behavior",
        checks=[VerificationCheck(
            layer="L3", target="d.md", claim_type="behavior",
            claim_text="behavior", verified=True, status="passed",
            detail="audit verdict",
        )],
    )
    layers["L4"] = LayerReport(
        layer="L4", name="Cross-language",
        checks=[
            VerificationCheck(
                layer="L4", target="d.md", claim_type="l4a_mechanical",
                claim_text="parity", verified=True, status="passed", detail="ok",
            ),
            VerificationCheck(
                layer="L4", target="d.md", claim_type="l4b_semantic",
                claim_text="prose", verified=True, status="passed",
                detail="audit verdict",
            ),
        ],
    )
    layers["L5"] = LayerReport(
        layer="L5", name="Epistemic",
        checks=[VerificationCheck(
            layer="L5", target="d.md", claim_type="epistemic",
            claim_text="epistemic", verified=True, status="passed",
            detail="audit verdict",
        )],
    )
    report = ComprehensiveVerificationReport(layers=layers)
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    # Valid audit verdicts are honoured, never reset to pending.
    assert result.pending_llm_layers == []
    assert result.semantic_complete is True
    assert result.l3_status == "passed"
    assert result.l4b_status == "passed"
    assert result.l5_status == "passed"
    assert result.verdict == "passed"
    assert result.ci_exit_code == 0
