"""Unit tests for L1 Existence Verifier."""

from pathlib import Path

from makewiki_skills.model.document_artifact import GeneratedDocument
from makewiki_skills.verification.l1_existence import L1ExistenceVerifier


def test_l1_generic_command_marked_generic_shell_semantics(tmp_path: Path):
    doc = GeneratedDocument(
        filename="install.md",
        base_name="install.md",
        language_code="en",
        content="# Installation\n```bash\ngit clone <url>\ncd repo\npip install -e .\n```\n",
    )
    verifier = L1ExistenceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L1"
    # Generic shell commands are candidates, not proven existence: the layer is
    # pending, never a vacuous pass.
    assert report.verdict == "pending"
    assert report.passed is False

    generic_checks = [
        c for c in report.checks if c.verification_source == "generic_shell_semantics"
    ]
    assert len(generic_checks) >= 2


def test_l1_generic_prefix_is_pending_not_passed(tmp_path: Path):
    """A generic-shell-prefix command must be a pending LLM candidate, never passed.

    Merely starting with ``git`` / ``pip`` / ``cd`` does not prove the command
    exists in THIS repository.
    """
    doc = GeneratedDocument(
        filename="install.md",
        base_name="install.md",
        language_code="en",
        content="# Installation\n```bash\npip install -e .\n```\n",
    )
    verifier = L1ExistenceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    gen = [c for c in report.checks if "pip install -e ." in c.claim_text]
    assert len(gen) == 1
    assert gen[0].verified is False
    assert gen[0].status == "pending"
    assert gen[0].verification_source == "generic_shell_semantics"
    assert not report.passed


def test_l1_repository_command_marked_verified_from_repository(tmp_path: Path):
    (tmp_path / "Makefile").write_text("build:\n\techo build\n", encoding="utf-8")
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmake build\n```\n",
    )
    verifier = L1ExistenceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    repo_checks = [
        c for c in report.checks if c.verification_source == "verified_from_repository" and c.claim_type == "command"
    ]
    assert len(repo_checks) == 1
    assert repo_checks[0].verified
    assert repo_checks[0].claim_text == "make build"


def test_l1_hedged_command_marked_hedging_caveat(tmp_path: Path):
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmyapp unknown-subcommand\n```\n> [!NOTE]\n> Note: This command is inferred.\n",
    )
    verifier = L1ExistenceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    hedged_checks = [
        c for c in report.checks if c.verification_source == "hedging_caveat"
    ]
    assert len(hedged_checks) == 1
    # A hedging caveat is a signal the command's existence was not established —
    # it is a pending candidate for the LLM, never a vacuous pass (mirrors L5's
    # treatment of the same hedged signal).
    assert hedged_checks[0].status == "pending"
    assert not hedged_checks[0].verified


def test_l1_hedged_command_is_pending_not_passed(tmp_path: Path):
    """The hedged-caveat heuristic must not elevate a command to 'passed'.

    Regression guard: this check previously emitted ``verified=True/status=passed``
    purely because the doc hedged about it, even though Python established no
    repository evidence for the command's existence.
    """
    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nmyapp unknown-subcommand\n```\n> [!NOTE]\n> Note: This command is inferred.\n",
    )
    verifier = L1ExistenceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    hedged_checks = [
        c for c in report.checks if c.verification_source == "hedging_caveat"
    ]
    assert len(hedged_checks) == 1
    assert hedged_checks[0].status == "pending"
    assert not hedged_checks[0].verified
    # A layer carrying only this hedged candidate must not report "passed".
    assert report.verdict == "pending"
    assert report.passed is False
def test_l1_missing_path_fails(tmp_path: Path):
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# Overview\nSee `./nonexistent_directory/file.py`.",
    )
    verifier = L1ExistenceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert not report.passed
    assert any(c.claim_type == "path" and not c.verified for c in report.checks)
