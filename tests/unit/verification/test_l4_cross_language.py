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


def test_stable_block_id_parity():
    """ID-tagged blocks are matched by [[id:...]] and compared by SHA256."""
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content=(
                    "# Usage\n"
                    "[[id:install.init]]\n```bash\napp init --force\n```\n"
                    "[[id:install.build]]\n```bash\napp build\n```\n"
                ),
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content=(
                    "# 使用\n"
                    "[[id:install.init]]\n```bash\napp init --force\n```\n"
                ),
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    mech = [c for c in report.checks if c.claim_type == "l4a_mechanical"]
    init = next(c for c in mech if "install.init" in c.claim_text)
    # Identical body across languages -> passed.
    assert init.verified is True
    assert init.status == "passed"
    # install.build is missing from zh-CN -> failed.
    build = next(c for c in mech if "install.build" in c.claim_text)
    assert build.verified is False
    assert build.status == "failed"


def test_stable_block_id_divergence_detected():
    """A block sharing an ID but with a divergent body is a mechanical failure."""
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n[[id:install.init]]\n```bash\napp init --force\n```\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="# 使用\n[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    init = next(
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "install.init" in c.claim_text
    )
    assert init.verified is False
    assert init.status == "failed"
    assert "differs" in init.detail.lower()


def test_semantic_sections_use_stable_id():
    """L4b prose parity is always a pending LLM check, never auto-passed."""
    docs = {
        "en": [
            GeneratedDocument(
                filename="guide.md",
                base_name="guide.md",
                language_code="en",
                content="# Guide\nEnglish prose here.\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="guide.zh-CN.md",
                base_name="guide.md",
                language_code="zh-CN",
                content="# 指南\n这里的中文正文。\n",
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    l4b = [c for c in report.checks if c.claim_type == "l4b_semantic"]
    assert len(l4b) == 1
    assert l4b[0].status == "pending"
    assert l4b[0].verified is False
    # Prose parity alone can never make the layer "passed".
    assert report.verdict in ("pending", "failed")
