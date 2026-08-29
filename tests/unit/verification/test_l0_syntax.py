"""Unit tests for L0 Syntax Verifier."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l0_syntax import L0SyntaxVerifier


def test_l0_syntax_valid_document():
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# Project Title\n\n## Overview\nThis is a valid document.\n\n### Details\nSequential headings.",
    )
    verifier = L0SyntaxVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L0"
    assert report.passed
    assert report.score == 1.0


def test_l0_syntax_flags_empty_document():
    doc = GeneratedDocument(
        filename="empty.md",
        base_name="empty.md",
        language_code="en",
        content="# Empty\n",
    )
    verifier = L0SyntaxVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert not report.passed
    assert any(c.status == "failed" and "empty" in c.detail.lower() for c in report.checks)


def test_l0_syntax_flags_heading_skips():
    doc = GeneratedDocument(
        filename="bad_headings.md",
        base_name="bad_headings.md",
        language_code="en",
        content="# Title\n\n### Subsubheading Jumped\nSkipped H2.",
    )
    verifier = L0SyntaxVerifier()
    report = verifier.verify_documents({"en": [doc]})

    assert any("jumped" in c.detail.lower() for c in report.checks)
