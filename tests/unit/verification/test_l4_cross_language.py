"""Unit tests for L4 Cross-Language Verifier."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l4_cross_language import L4CrossLanguageVerifier


def test_l4_cross_language_no_deltas_is_pending_not_passed():
    # Identical commands across languages -> the reviewer finds no deltas and no
    # per-claim comparison check is emitted. The layer must NOT report a vacuous
    # pass; it reports a single pending check awaiting LLM judgment.
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n```bash\nmyapp run --port 8080\n```\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="# 使用\n```bash\nmyapp run --port 8080\n```\n",
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    assert report.layer == "L4"
    assert len(report.checks) == 1
    assert report.checks[0].status == "pending"
    assert report.checks[0].verified is False
    assert report.score == 0.0


def test_l4_single_language_is_not_applicable_not_passed():
    # A single language means parity is genuinely not applicable; it must not be
    # reported as passed.
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n```bash\nmyapp run\n```\n",
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    assert report.layer == "L4"
    assert len(report.checks) == 1
    assert report.checks[0].status == "not_applicable"
    assert report.checks[0].verified is False


def test_l4_cross_language_missing_command_detected():
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n```bash\nmyapp run --port 8080\n```\n```bash\nmyapp status\n```\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="# 使用\n```bash\nmyapp run --port 8080\n```\n",
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    assert not report.passed
    assert any("myapp status" in c.claim_text for c in report.checks)
