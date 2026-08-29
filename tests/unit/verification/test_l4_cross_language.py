"""Unit tests for L4 Cross-Language Verifier."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l4_cross_language import L4CrossLanguageVerifier


def test_l4_cross_language_parity_passed():
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
    assert report.passed
    assert report.score == 1.0


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
