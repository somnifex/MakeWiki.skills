"""Unit tests for L4 Cross-Language Verifier."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l4_cross_language import (
    L4CrossLanguageVerifier,
    pair_blocks_by_section_id,
    render_section_marker,
    section_ids,
)


def test_l4_cross_language_no_deltas_is_pending_not_passed():
    # Identical, ID-tagged commands across languages -> reviewer finds no deltas,
    # no per-claim comparison failure and no untagged-block failure. The layer
    # must NOT report a vacuous pass; it reports a pending L4b check awaiting
    # LLM judgment, so the verdict stays pending.
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content=(
                    "# Usage\n"
                    "[[id:run]]\n```bash\nmyapp run --port 8080\n```\n"
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
                    "[[id:run]]\n```bash\nmyapp run --port 8080\n```\n"
                ),
            )
        ],
    }
    verifier = L4CrossLanguageVerifier()
    report = verifier.verify_documents(docs)

    assert report.layer == "L4"
    # No mechanical failure under correct semantics.
    assert not any(c.status == "failed" for c in report.checks)
    l4b = [c for c in report.checks if c.claim_type == "l4b_semantic"]
    assert len(l4b) == 1
    assert l4b[0].status == "pending"
    assert l4b[0].verified is False
    # Pending semantic review keeps the layer honest (never a vacuous pass).
    assert report.verdict == "pending"
    assert not report.passed


def test_l4_single_language_is_not_applicable_not_passed():
    # A single language means parity is genuinely not applicable; it must not be
    # reported as passed. Both L4 sub-layers are represented — L4a (mechanical)
    # and L4b (semantic) — and each is not_applicable, never verified/passed.
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
    # The L4a (mechanical) and L4b (semantic) sub-layers are both reported
    # NOT APPLICABLE for a single generated language — parity is genuinely
    # inapplicable, never a vacuous pass. Each is explicitly not verified.
    assert len(report.checks) == 2
    assert {c.claim_type for c in report.checks} == {"l4a_mechanical", "l4b_semantic"}
    for check in report.checks:
        assert check.status == "not_applicable"
        assert check.verified is False


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


# ---------------------------------------------------------------------------
# Untagged technical block audit (finding 1)
# ---------------------------------------------------------------------------


def test_untagged_technical_block_fails_and_flips_layer():
    """An untagged technical fence yields an L4a FAILED check with untagged reason,
    and that failed check flips the whole layer verdict to failed."""
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n```bash\nmyapp run\n```\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="# 使用\n```bash\nmyapp run\n```\n",
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)

    untagged = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "Untagged technical" in c.claim_text
    ]
    assert len(untagged) >= 1
    for check in untagged:
        assert check.status == "failed"
        assert check.verified is False
        # Distinguishes this from the "missing block" / "diverged" reasons.
        assert "untagged" in check.detail.lower() or "bypass" in check.detail.lower()
    # The failed untagged check flips the layer verdict to failed.
    assert report.verdict == "failed"
    assert not report.passed


def test_tagged_technical_block_produces_no_untagged_failure():
    """The same fence tagged [[id:x]] does not trigger an untagged-block failure."""
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="# Usage\n[[id:run]]\n```bash\nmyapp run\n```\n",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="# 使用\n[[id:run]]\n```bash\nmyapp run\n```\n",
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)

    assert not any(
        c.claim_type == "l4a_mechanical" and "Untagged technical" in c.claim_text
        for c in report.checks
    )
    # The tagged block is provably present and identical -> its parity check passes.
    run = next(
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "identical" in c.claim_text and "run" in c.claim_text
    )
    assert run.status == "passed"


def test_parity_ignore_exempts_untagged_technical_block():
    """An untagged technical block with [[parity:ignore ...]] is passed (exempted),
    not failed."""
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content=(
                    "# Usage\n"
                    '[[parity:ignore reason="illustrative snippet"]]\n'
                    "```bash\nmyapp run --demo\n```\n"
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
                    '[[parity:ignore reason="illustrative snippet"]]\n'
                    "```bash\nmyapp run --demo\n```\n"
                ),
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)

    exempted = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "exempted" in c.claim_text
    ]
    assert len(exempted) >= 1
    for check in exempted:
        assert check.status == "passed"
        assert check.verified is True
    # None of the exempted blocks are reported as failures.
    assert not any(
        c.claim_type == "l4a_mechanical" and "Untagged technical" in c.claim_text
        for c in report.checks
    )


# ---------------------------------------------------------------------------
# Stable section pairing (finding 2)
# ---------------------------------------------------------------------------


def test_section_ids_and_render_round_trip():
    """section_ids/render_section_marker round-trip."""
    slug = "getting-started"
    marker = render_section_marker(slug)
    assert marker == "<!-- makewiki:section=getting-started -->"
    doc = f"# Doc\n\n{marker}\n\nSome prose.\n"
    assert section_ids(doc) == [slug]

    # Multiple markers, in document order.
    doc2 = (
        "<!-- makewiki:section=alpha -->\nA\n"
        "<!-- makewiki:section=beta -->\nB\n"
    )
    assert section_ids(doc2) == ["alpha", "beta"]


def test_blocks_in_reordered_sections_still_pair():
    """Same section marker + block id across languages, in DIFFERENT section
    order, still pairs; parity passes for exact-equal code."""
    en = (
        "<!-- makewiki:section=usage -->\n"
        "# Usage\n"
        "[[id:run]]\n```bash\napp run\n```\n"
        "\n"
        "<!-- makewiki:section=install -->\n"
        "# Install\n"
        "[[id:install.init]]\n```bash\napp init\n```\n"
    )
    # zh-CN reorders: install section first, usage second.
    zh = (
        "<!-- makewiki:section=install -->\n"
        "# 安装\n"
        "[[id:install.init]]\n```bash\napp init\n```\n"
        "\n"
        "<!-- makewiki:section=usage -->\n"
        "# 用法\n"
        "[[id:run]]\n```bash\napp run\n```\n"
    )

    paired = pair_blocks_by_section_id({"en": en, "zh-CN": zh})
    # Both blocks pair under the SAME (section, block) key despite reordering.
    assert ("usage", "run") in paired
    assert ("install", "install.init") in paired
    assert set(paired[("usage", "run")].keys()) == {"en", "zh-CN"}
    assert set(paired[("install", "install.init")].keys()) == {"en", "zh-CN"}

    # Verifier: parity passes for the exact-equal code even though section order
    # differs.
    docs = {
        "en": [GeneratedDocument(filename="g.md", base_name="g.md", language_code="en", content=en)],
        "zh-CN": [
            GeneratedDocument(
                filename="g.zh-CN.md", base_name="g.md", language_code="zh-CN", content=zh
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)
    mech = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical"
    ]
    # Both blocks are matched and identical -> each gets a passed parity check.
    for block_id in ("run", "install.init"):
        assert any(
            "identical" in c.claim_text and block_id in c.claim_text and c.status == "passed"
            for c in mech
        )
    assert not any(
        c.status == "failed"
        for c in mech
        if "Untagged technical" not in c.claim_text and "missing" not in c.claim_text
    )


def test_pairing_falls_back_to_block_id_without_section_markers():
    """No section markers in any doc -> falls back to pairing by block ID alone."""
    en = "[[id:run]]\n```bash\napp run\n```\n"
    zh = "[[id:run]]\n```bash\napp run\n```\n"
    paired = pair_blocks_by_section_id({"en": en, "zh-CN": zh})
    # Section key collapses to "" and the block still pairs.
    assert ("", "run") in paired
    assert set(paired[("", "run")].keys()) == {"en", "zh-CN"}

