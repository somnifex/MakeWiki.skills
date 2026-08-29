"""Contract: no verification status may be "passed" unless it was actually checked.

These tests construct the in-memory cases that previously false-passed and assert
they now resolve to ``pending`` or ``failed``/``not_applicable`` - never ``passed``.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.model.claim import (
    Claim,
    ClaimEvidence,
    ClaimSet,
    verify_claims_against_codebase,
)
from makewiki_skills.verification.l3_behavior import L3BehaviorVerifier
from makewiki_skills.verification.l4_cross_language import L4CrossLanguageVerifier
from makewiki_skills.verification.l5_epistemic import L5EpistemicVerifier
from makewiki_skills.verification.quality_gate import _layer_status
from makewiki_skills.verification.report import (
    ComprehensiveVerificationReport,
    LayerReport,
    VerificationCheck,
)


def test_l5_never_auto_passed_on_high_confidence():
    """A high-confidence claim must not be auto-marked L5 passed (no check ran)."""
    claim = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
        confidence="high",
        evidence=[
            ClaimEvidence(
                source_file="src/cli.py",
                raw_text="@app.command()\ndef run(): ...",
                confidence="high",
            )
        ],
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[claim]), Path("."))
    assert verified.get_by_id("CMD_RUN").verification.l5_epistemic == "pending"


def test_l0_malformed_claim_is_not_passed():
    """A syntactically malformed claim must be L0 failed/pending, never passed."""
    malformed = Claim(
        claim_id="not_a_valid_id!",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[malformed]), Path("."))
    assert verified.get_by_id("not_a_valid_id!").verification.l0_syntax == "failed"


def test_l3_unmatched_error_symptom_is_not_passed(tmp_path: Path):
    """A documented error symptom not found in source is failed/pending, never passed."""
    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content='# Troubleshooting\nSymptom: `"phantom subsystem down"` appears at startup.',
    )
    report = L3BehaviorVerifier(tmp_path).verify_documents({"en": [doc]})

    err_checks = [c for c in report.checks if "phantom subsystem down" in c.claim_text]
    assert len(err_checks) == 1
    assert err_checks[0].status != "passed"
    assert err_checks[0].verified is False


def test_empty_l3_layer_is_pending(tmp_path: Path):
    """A layer with no actual checks must be pending, not passed."""
    doc = GeneratedDocument(
        filename="guide.md",
        base_name="guide.md",
        language_code="en",
        content="# Guide\nPlain prose with no errors or exit codes.",
    )
    report = L3BehaviorVerifier(tmp_path).verify_documents({"en": [doc]})
    assert report.checks
    assert all(c.status != "passed" for c in report.checks)


def test_empty_l4_layer_is_not_passed():
    """An L4 layer with no parity comparison must be pending/not_applicable."""
    # Single language -> parity genuinely not applicable.
    single = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n```bash\nmyapp run\n```\n",
            )
        ],
    }
    report1 = L4CrossLanguageVerifier().verify_documents(single)
    assert all(c.status != "passed" for c in report1.checks)
    assert report1.checks[0].status == "not_applicable"

    # Two languages with identical commands -> reviewer finds no deltas, no real
    # comparison check emitted -> layer is pending, not passed.
    twin = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n```bash\nmyapp run\n```\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="# 使用\n```bash\nmyapp run\n```\n",
            )
        ],
    }
    report2 = L4CrossLanguageVerifier().verify_documents(twin)
    assert report2.checks
    assert all(c.status != "passed" for c in report2.checks)


def test_empty_l5_layer_is_pending():
    """An L5 layer with no commands checked must be pending, not passed."""
    doc = GeneratedDocument(
        filename="intro.md",
        base_name="intro.md",
        language_code="en",
        content="# Intro\nPlain prose without any commands.",
    )
    report = L5EpistemicVerifier().verify_documents({"en": [doc]})
    assert report.checks
    assert all(c.status != "passed" for c in report.checks)


def test_empty_layers_resolve_to_pending_in_gate():
    """A vacuous L3/L4/L5 layer must resolve to 'pending' in the quality gate,
    never a false 'passed'."""
    for layer in ("L3", "L4", "L5"):
        report = ComprehensiveVerificationReport(
            layers={
                layer: LayerReport(
                    layer=layer,
                    name=layer,
                    checks=[
                        # Mirrors the honest empty-layer fallback emitted by the
                        # verifiers: verified=False with a pending (or
                        # not_applicable) status - never a vacuous pass.
                        VerificationCheck(
                            layer=layer,
                            target="all",
                            claim_type="structure",
                            claim_text="fallback",
                            verified=False,
                            status="pending",
                            verification_source="not_executed",
                            detail="layer pending",
                        )
                    ],
                )
            }
        )
        assert _layer_status(report, layer) == "pending"
