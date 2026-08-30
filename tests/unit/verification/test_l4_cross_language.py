"""Unit tests for L4 Cross-Language Verifier."""

from makewiki_skills.model.document_artifact import GeneratedDocument
from makewiki_skills.review.section_parser import parse_document_sections
from makewiki_skills.verification.l4_cross_language import (
    L4CrossLanguageVerifier,
    pair_blocks_by_section_id,
    render_section_marker,
    section_ids,
    split_sections,
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
    # Reviewable sections use H2 headings (an H2 following the marker). The zh-CN
    # version reorders the sections relative to en.
    en = (
        "<!-- makewiki:section=usage -->\n"
        "## Usage\n"
        "[[id:run]]\n```bash\napp run\n```\n"
        "\n"
        "<!-- makewiki:section=install -->\n"
        "## Install\n"
        "[[id:install.init]]\n```bash\napp init\n```\n"
    )
    # zh-CN reorders: install section first, usage second.
    zh = (
        "<!-- makewiki:section=install -->\n"
        "## 安装\n"
        "[[id:install.init]]\n```bash\napp init\n```\n"
        "\n"
        "<!-- makewiki:section=usage -->\n"
        "## 用法\n"
        "[[id:run]]\n```bash\napp run\n```\n"
    )

    docs = {
        "en": [
            GeneratedDocument(filename="g.md", base_name="g.md", language_code="en", content=en)
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="g.zh-CN.md", base_name="g.md", language_code="zh-CN", content=zh
            )
        ],
    }
    paired = pair_blocks_by_section_id(docs)
    # Both blocks pair under the SAME (document, section, block) key despite
    # reordering.
    assert ("g.md", "usage", "run") in paired
    assert ("g.md", "install", "install.init") in paired
    assert set(paired[("g.md", "usage", "run")].keys()) == {"en", "zh-CN"}
    assert set(paired[("g.md", "install", "install.init")].keys()) == {"en", "zh-CN"}

    # Verifier: parity passes for the exact-equal code even though section order
    # differs.
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
    """No section markers in any doc -> falls back to keying by (doc, "", block)."""
    en = "[[id:run]]\n```bash\napp run\n```\n"
    zh = "[[id:run]]\n```bash\napp run\n```\n"
    docs = {
        "en": [
            GeneratedDocument(filename="g.md", base_name="g.md", language_code="en", content=en)
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="g.zh-CN.md", base_name="g.md", language_code="zh-CN", content=zh
            )
        ],
    }
    paired = pair_blocks_by_section_id(docs)
    # Section key collapses to "" (document_id is always the explicit base_name)
    # and the block still pairs.
    assert ("g.md", "", "run") in paired
    assert set(paired[("g.md", "", "run")].keys()) == {"en", "zh-CN"}


# ---------------------------------------------------------------------------
# Splitting delegates to the parser (single source of truth)
# ---------------------------------------------------------------------------


def test_split_sections_matches_parser():
    """split_sections is a thin wrapper over parse_document_sections: the section
    ids and body content they produce must agree."""
    sample = (
        "<!-- makewiki:section=alpha -->\n"
        "## Alpha\n"
        "Body a.\n"
        "<!-- makewiki:section=beta -->\n"
        "## Beta\n"
        "Body b.\n"
    )
    parsed = parse_document_sections(sample, document_id="g.md")
    split = split_sections(sample)

    assert [sid for sid, _ in split] == [sec.section_id for sec in parsed.sections]
    assert [content for _, content in split] == [sec.content for sec in parsed.sections]


# ---------------------------------------------------------------------------
# Stable-identity structural invariants (§8 / §9)
# ---------------------------------------------------------------------------


def test_duplicate_section_id_fails():
    """One document declaring the same stable section id twice yields an L4a
    FAILED check; a section ID must be unique per document."""
    dup = (
        "<!-- makewiki:section=alpha -->\n## Alpha\ncontent a\n"
        "<!-- makewiki:section=alpha -->\n## Alpha again\ncontent b\n"
    )
    docs = {
        "en": [GeneratedDocument(filename="x.md", base_name="x.md", language_code="en", content=dup)],
        "zh-CN": [
            GeneratedDocument(
                filename="x.zh-CN.md", base_name="x.md", language_code="zh-CN", content=dup
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)

    dup_checks = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "more than once" in c.claim_text
    ]
    assert len(dup_checks) >= 1
    for check in dup_checks:
        assert check.status == "failed"
        assert check.verified is False
        assert "alpha" in check.claim_text


def test_duplicate_block_id_fails():
    """One document with two [[id:run]] blocks in different sections is an L4a
    FAILED check naming the duplicated block id (not silently overwritten)."""
    content = (
        "<!-- makewiki:section=alpha -->\n## Alpha\n"
        "[[id:run]]\n```bash\napp run a\n```\n"
        "<!-- makewiki:section=beta -->\n## Beta\n"
        "[[id:run]]\n```bash\napp run b\n```\n"
    )
    docs = {
        "en": [GeneratedDocument(filename="x.md", base_name="x.md", language_code="en", content=content)],
        "zh-CN": [
            GeneratedDocument(
                filename="x.zh-CN.md", base_name="x.md", language_code="zh-CN", content=content
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)

    dup_checks = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical"
        and "Duplicate stable block id" in c.claim_text
    ]
    assert len(dup_checks) >= 1
    for check in dup_checks:
        assert check.status == "failed"
        assert check.verified is False
        assert check.target == "[[id:run]]"


def test_same_block_id_different_documents_does_not_collide():
    """Two documents each declaring [[id:install.command]] do NOT collide: the
    pairing keys are namespaced by document_id and parity succeeds for each."""
    block = "[[id:install.command]]\n```bash\nhelm install app\n```\n"
    a_en = f"<!-- makewiki:section=install -->\n## Install\n{block}"
    b_en = f"<!-- makewiki:section=install -->\n## Install\n{block}"
    a_zh = f"<!-- makewiki:section=install -->\n## 安装\n{block}"
    b_zh = f"<!-- makewiki:section=install -->\n## 安装\n{block}"

    docs = {
        "en": [
            GeneratedDocument(filename="a.md", base_name="a.md", language_code="en", content=a_en),
            GeneratedDocument(filename="b.md", base_name="b.md", language_code="en", content=b_en),
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="a.zh-CN.md", base_name="a.md", language_code="zh-CN", content=a_zh
            ),
            GeneratedDocument(
                filename="b.zh-CN.md", base_name="b.md", language_code="zh-CN", content=b_zh
            ),
        ],
    }

    paired = pair_blocks_by_section_id(docs)
    # Both documents' install.command blocks are kept separate by document_id.
    assert ("a.md", "install", "install.command") in paired
    assert ("b.md", "install", "install.command") in paired
    assert set(paired[("a.md", "install", "install.command")].keys()) == {"en", "zh-CN"}
    assert set(paired[("b.md", "install", "install.command")].keys()) == {"en", "zh-CN"}

    report = L4CrossLanguageVerifier().verify_documents(docs)
    # Each document's install.command block is present in both languages and
    # identical -> both pass; no cross-document collision failure.
    passed = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "identical" in c.claim_text
    ]
    assert any(c.target == "a.md [[id:install.command]] @install" for c in passed)
    assert any(c.target == "b.md [[id:install.command]] @install" for c in passed)


def test_missing_multilingual_section_id_fails():
    """In multilingual output, a language's H2 with no section marker is an L4a
    FAILED check mentioning 'stable section marker'."""
    en = (
        "<!-- makewiki:section=setup -->\n## Setup\nRun the app.\n"
    )
    # zh-CN H2 carries no stable section marker.
    zh = "## 设置\n运行应用。\n"
    docs = {
        "en": [
            GeneratedDocument(filename="guide.md", base_name="guide.md", language_code="en", content=en)
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="guide.zh-CN.md", base_name="guide.md", language_code="zh-CN", content=zh
            )
        ],
    }
    report = L4CrossLanguageVerifier().verify_documents(docs)

    missing = [
        c for c in report.checks
        if c.claim_type == "l4a_mechanical" and "stable section marker" in c.claim_text
    ]
    assert len(missing) >= 1
    for check in missing:
        assert check.status == "failed"
        assert check.verified is False
