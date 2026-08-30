"""Unit tests for L3 Behavior Verifier."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l3_behavior import L3BehaviorVerifier


def test_l3_behavior_exit_code(tmp_path: Path):
    # tmp_path has no Python source returning exit code 1, so the documented
    # exit code cannot be traced: it must be a pending LLM candidate, not passed.
    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content="# Troubleshooting\nWhen a configuration is invalid, the tool terminates with exit code 1.",
    )
    verifier = L3BehaviorVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L3"
    assert report.passed is False
    assert report.verdict == "pending"
    exit_checks = [
        c for c in report.checks if "exit code 1" in c.claim_text.lower()
    ]
    assert len(exit_checks) == 1
    assert exit_checks[0].verified is False
    assert exit_checks[0].status == "pending"
    assert exit_checks[0].verification_source == "heuristic"


def test_l3_common_exit_code_does_not_auto_pass(tmp_path: Path):
    """Exit code 1 is common - Python must NOT auto-pass it without a call site."""
    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content="# Troubleshooting\nThe CLI terminates with exit code 1 on error.",
    )
    verifier = L3BehaviorVerifier(tmp_path)
    # No Python source in tmp_path.
    report = verifier.verify_documents({"en": [doc]})

    exit_checks = [c for c in report.checks if "exit code 1" in c.claim_text.lower()]
    assert len(exit_checks) == 1
    assert exit_checks[0].status == "pending"
    assert exit_checks[0].verified is False


def test_l3_exit_code_traced_in_repository_passes(tmp_path: Path):
    """When a real call site returns exit code 3, the documented code is verifiable."""
    (tmp_path / "app.py").write_text(
        "import sys\nif __name__ == '__main__':\n    sys.exit(3)\n",
        encoding="utf-8",
    )
    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content="# Troubleshooting\nThe process terminates with exit code 3.",
    )
    verifier = L3BehaviorVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    exit_checks = [c for c in report.checks if "exit code 3" in c.claim_text.lower()]
    assert len(exit_checks) == 1
    assert exit_checks[0].verified is True
    assert exit_checks[0].status == "passed"
    assert exit_checks[0].verification_source == "verified_from_repository"


def test_l3_behavior_error_message_match(tmp_path: Path):
    src = """
def run():
    raise ValueError("Configuration file not found or invalid format")
"""
    (tmp_path / "app.py").write_text(src, encoding="utf-8")

    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content='# Troubleshooting\nSymptom: `"Configuration file not found"` error during initialization.',
    )
    verifier = L3BehaviorVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert report.passed
    err_checks = [c for c in report.checks if "Configuration file not found" in c.claim_text]
    assert len(err_checks) == 1
    assert err_checks[0].verified


def test_l3_unmatched_error_symptom_is_pending_not_passed(tmp_path):
    # tmp_path has no Python source, so the documented symptom cannot be matched
    # to any declared handler. It must never be reported as passed.
    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content='# Troubleshooting\nSymptom: `"mystery component failed"` during startup.',
    )
    verifier = L3BehaviorVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    err_checks = [c for c in report.checks if "mystery component failed" in c.claim_text]
    assert len(err_checks) == 1
    assert err_checks[0].verified is False
    assert err_checks[0].status == "pending"
    assert err_checks[0].verification_source == "heuristic"


def test_l3_empty_layer_is_pending_not_passed(tmp_path):
    # A document with no error/exit-code content yields no real L3 checks; the
    # layer must report pending, never a vacuous pass.
    doc = GeneratedDocument(
        filename="guide.md",
        base_name="guide.md",
        language_code="en",
        content="# Guide\nJust some plain prose without errors or exit codes.",
    )
    verifier = L3BehaviorVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert len(report.checks) == 1
    assert report.checks[0].status == "pending"
    assert report.checks[0].verified is False
