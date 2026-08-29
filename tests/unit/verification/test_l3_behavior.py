"""Unit tests for L3 Behavior Verifier."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l3_behavior import L3BehaviorVerifier


def test_l3_behavior_exit_code(tmp_path: Path):
    doc = GeneratedDocument(
        filename="troubleshooting.md",
        base_name="troubleshooting.md",
        language_code="en",
        content="# Troubleshooting\nWhen a configuration is invalid, the tool terminates with exit code 1.",
    )
    verifier = L3BehaviorVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L3"
    assert report.passed
    assert any("exit code 1" in c.claim_text.lower() for c in report.checks)


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
