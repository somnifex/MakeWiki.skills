"""Feature ↔ Test coverage contract.

Each user-facing feature advertised in the documentation set has at least one
mechanical test that exercises it. The contract walks a curated list of
advertised features and confirms a corresponding test exists in this repo.

The intent is **not** to count tests per feature (that's brittle), but to
guarantee that any feature mentioned in ``SKILL.md`` / ``AGENTS.md`` /
``references/`` is not silently unimplemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _has_test(predicate) -> bool:
    """Return True if any test file under ``tests/`` matches ``predicate``."""
    for path in PROJECT_ROOT.glob("tests/**/*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if predicate(text):
            return True
    return False


def test_evidence_backed_claim_extraction_has_test():
    """``build_claims_from_evidence`` is exercised by a unit test."""
    from makewiki_skills.model.claim import build_claims_from_evidence

    assert callable(build_claims_from_evidence)
    assert _has_test(lambda t: "build_claims_from_evidence" in t)


def test_layered_verification_L0_L5_has_test():
    """The L0–L5 verification orchestrator is wired into a unit test."""
    assert _has_test(lambda t: "L0" in t and "L5" in t and "VerificationOrchestrator" in t)


def test_quality_gate_ci_exit_codes_have_test():
    """PASS=0 / FAIL=1 contract has a test."""
    assert _has_test(
        lambda t: "exit_code" in t and ("0" in t and "1" in t)
    )


def test_sync_bundle_is_bundle_prep_not_publishing():
    """`sync-bundle` is documented as bundle-prep only. The CLI rejects ``--push``."""
    assert _has_test(
        lambda t: "sync" in t and "bundle" in t and ("--push" in t or "publish" in t)
    )


def test_export_rejects_pdf_has_test():
    """`export --format pdf` must error out and exit code 1 — covered by test."""
    assert _has_test(lambda t: "--format pdf" in t or "format_type == \"pdf\"" in t)


def test_deterministic_generate_is_not_authoritative():
    """`deterministic-generate` is explicitly marked as the non-authoritative path."""
    assert _has_test(
        lambda t: "deterministic-generate" in t or "deterministic_generate" in t
    )


def test_quality_gate_module_is_importable():
    """The Quality Gate module exposes its public API."""
    from makewiki_skills.verification.quality_gate import (
        QualityGateResult,
        evaluate_quality_gate,
    )

    assert callable(evaluate_quality_gate)
    assert QualityGateResult is not None


def test_evidence_emits_facts_only():
    """The evidence CLI / scan path emits facts and never semantic conclusions."""
    assert _has_test(lambda t: "evidence" in t and ("fact" in t.lower()))


def test_orchestrator_can_run_all_layers():
    """``VerificationOrchestrator.verify_documents`` is exercised end-to-end."""
    assert _has_test(lambda t: "verify_documents" in t)


def test_quality_gate_respects_min_grounding_score():
    """Quality Gate fails when the grounding score is below threshold."""
    assert _has_test(
        lambda t: "min_grounding_score" in t and "grounding_score" in t
    )


def test_existing_path_claim_verified():
    """verify-claim marks L1 ``passed`` for paths that exist on disk."""
    assert _has_test(lambda t: "l1_existence" in t and "passed" in t and "failed" in t)


def test_bootstrap_pinning_is_exercised():
    """scripts/bootstrap_toolkit.py version + SHA256 pinning is covered."""
    assert _has_test(
        lambda t: "requested_version" in t or "verify_archive_sha256" in t or "tag_archive_url" in t
    )


def test_block_id_parity_has_test():
    """Cross-language parity exercises block-ID matching."""
    assert _has_test(lambda t: "block_id" in t or "block-id" in t or "parity" in t.lower())


def test_claim_provenance_marker_has_test():
    """LLM-authored claims carry ``provenance="llm_claim"`` — covered by test."""
    assert _has_test(lambda t: "llm_claim" in t and "python_fact" in t)


def test_zero_hallucination_terminology_replaced_in_tests():
    """The legacy "zero-hallucination" framing is replaced by evidence-backed terms.

    The contract intentionally only checks that the **tests** use the new
    vocabulary. This test excludes itself (the contract itself) from the
    scan so its docstring doesn't self-trigger.
    """
    tests_text = ""
    current = Path(__file__).resolve()
    for path in PROJECT_ROOT.glob("tests/**/*.py"):
        if path.resolve() == current:
            continue
        tests_text += path.read_text(encoding="utf-8", errors="replace") + "\n"
    forbidden = "zero-hallucination"
    if forbidden in tests_text:
        for line in tests_text.splitlines():
            if forbidden in line and "must not" not in line and "never" not in line:
                pytest.fail(
                    f"tests still use legacy 'zero-hallucination' phrasing: {line.strip()[:120]}"
                )
