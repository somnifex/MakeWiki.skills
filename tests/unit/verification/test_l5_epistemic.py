"""Unit tests for L5 Epistemic Verifier."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l5_epistemic import L5EpistemicVerifier


def test_l5_epistemic_hedged_command_pending_candidate():
    """A hedged command is a pending epistemic candidate, never auto-passed."""
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmyapp speculative-cmd\n```\n> [!NOTE]\n> Note: This command is experimental.\n",
    )
    verifier = L5EpistemicVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L5"
    # Python cannot adjudicate epistemic correctness -> every check is pending.
    assert report.verdict == "pending"
    assert report.passed is False
    assert all(not c.verified for c in report.checks)
    assert all(c.status == "pending" for c in report.checks)
    assert any("speculative-cmd" in c.claim_text for c in report.checks)


def test_l5_epistemic_unhedged_speculation_is_pending():
    """An unhedged unfounded command is also pending - Python does not adjudicate it."""
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmyapp completely-unfounded-cmd\n```\n",
    )
    verifier = L5EpistemicVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert not report.passed
    cmd_checks = [c for c in report.checks if "completely-unfounded-cmd" in c.claim_text]
    assert len(cmd_checks) == 1
    assert cmd_checks[0].verified is False
    assert cmd_checks[0].status == "pending"


def test_l5_python_does_not_adjudicate_epistemics():
    """L5 must never emit a ``passed`` epistemic verdict from Python heuristics."""
    # Even the most "obviously fine" generic command yields a pending candidate.
    doc = GeneratedDocument(
        filename="install.md",
        base_name="install.md",
        language_code="en",
        content="# Install\n```bash\npip install -e .\n```\n",
    )
    verifier = L5EpistemicVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert len(report.checks) >= 1
    assert all(c.status == "pending" for c in report.checks)
    assert all(not c.verified for c in report.checks)
    assert not report.passed


def test_l5_empty_layer_is_pending_not_passed():
    # A document with no commands means no L5 epistemic check actually ran; the
    # layer must report pending, never a vacuous pass.
    doc = GeneratedDocument(
        filename="intro.md",
        base_name="intro.md",
        language_code="en",
        content="# Intro\nSome plain prose without any commands.",
    )
    verifier = L5EpistemicVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert len(report.checks) == 1
    assert report.checks[0].status == "pending"
    assert report.checks[0].verified is False
