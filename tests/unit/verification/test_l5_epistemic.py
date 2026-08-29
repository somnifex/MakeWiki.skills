"""Unit tests for L5 Epistemic Verifier."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l5_epistemic import L5EpistemicVerifier


def test_l5_epistemic_hedged_command_passes():
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmyapp speculative-cmd\n```\n> [!NOTE]\n> Note: This command is experimental.\n",
    )
    verifier = L5EpistemicVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L5"
    assert report.passed
    assert all(c.verified for c in report.checks)


def test_l5_epistemic_unhedged_speculation_fails():
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmyapp completely-unfounded-cmd\n```\n",
    )
    verifier = L5EpistemicVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert not report.passed
    assert any("completely-unfounded-cmd" in c.claim_text and not c.verified for c in report.checks)


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
