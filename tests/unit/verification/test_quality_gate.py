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
    # L0/L1/L2 all pass and score is 1.0 -> gate passes even though L3 pending.
    assert result.passed is True


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
    """Pending L3/L4/L5 yields verdict=pending_semantic_review, honest but non-failing.

    The legacy ``passed`` bool and ``exit_code`` keep the historical
    allow-pending-True contract (passed=True / exit 0), while ``verdict`` and
    ``semantic_complete`` expose the true pending state.
    """
    report = _review_report(llm_pending=True)
    cfg = MakeWikiConfig.default(Path("."))
    cfg.quality.allow_pending_llm_layers = True
    result = evaluate_quality_gate(report, cfg)

    assert result.mechanical_passed is True
    assert result.verdict == "pending_semantic_review"
    assert result.semantic_complete is False
    assert set(result.pending_llm_layers) == {"L3", "L4", "L5"}
    # Legacy contract preserved: passed True / exit 0 for pending-LLM-when-allowed.
    assert result.passed is True
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
    mechanical layer must never yield a vacuous ``passed`` verdict.
    """
    report = _review_report(llm_pending=False)
    # Empty L2 (no interface facts extracted) -> LayerReport with no checks -> pending.
    report.layers["L2"] = LayerReport(layer="L2", name="Interface", checks=[])
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.verdict != "passed"  # honest: interface not proven
    assert result.interface_passed is False
    assert result.passed is False
    # Pending (not failed) -> exit 0, but the gate has NOT reported a clean pass.
    assert result.verdict == "pending_semantic_review"
    assert result.exit_code == 0
    assert result.semantic_complete is True  # nothing pending on the LLM side
