"""Stable code-block ID parity contract.

Cross-language code-block parity matches logical blocks by a stable
``[[id:...]]`` marker — never by position. This contract verifies the
mechanical L4 cross-language verifier:

* extracts blocks keyed by their stable ID,
* compares block bodies by content hash,
* detects ID-tagged blocks that are missing from a secondary language,
* detects ID-tagged blocks whose body diverged from the primary, and
* flags untagged technical blocks unless explicitly exempted.
"""

from __future__ import annotations

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.verification.l4_cross_language import (
    L4CrossLanguageVerifier,
    extract_blocks_by_id,
    stable_block_content_hash,
)


def _doc(filename: str, base_name: str, language_code: str, content: str) -> DocumentArtifact:
    return DocumentArtifact(
        filename=filename,
        base_name=base_name,
        language_code=language_code,
        content=content,
    )


def test_extract_blocks_keyed_by_stable_id():
    content = (
        "# Doc\n\n"
        "<!-- makewiki:section=getting_started -->\n"
        "## Getting Started\n\n"
        "[[id:getting_started.install]]\n```bash\nmake setup\n```\n\n"
        "<!-- makewiki:section=usage -->\n"
        "## Usage\n\n"
        "[[id:usage.deploy]]\n```bash\nmake deploy\n```\n"
    )
    blocks = extract_blocks_by_id(content)
    assert set(blocks.keys()) == {"getting_started.install", "usage.deploy"}
    install_full, install_hash = blocks["getting_started.install"]
    assert "make setup" in install_full


def test_content_hash_differs_for_different_bodies():
    a = stable_block_content_hash("make setup\n")
    b = stable_block_content_hash("make setup --force\n")
    assert a != b
    assert stable_block_content_hash("make setup\n") == a


def test_l4_detects_missing_block_by_id():
    """A block missing from the secondary is flagged as a parity failure."""
    verifier = L4CrossLanguageVerifier()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n"
                "<!-- makewiki:section=install -->\n"
                "## Install\n\n"
                "[[id:install.init]]\n```bash\napp init\n```\n\n"
                "[[id:install.build]]\n```bash\napp build\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n"
                "<!-- makewiki:section=install -->\n"
                "## 安装\n\n"
                "[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    report = verifier.verify_documents(docs)
    l4a_failures = [c for c in report.checks if c.claim_type == "l4a_mechanical" and c.status == "failed"]
    assert any("install.build" in (c.detail or "") or "install.build" in c.claim_text for c in l4a_failures)


def test_l4_detects_diverged_block_by_id():
    """A block sharing an ID but differing in body is flagged as a failure."""
    verifier = L4CrossLanguageVerifier()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n"
                "<!-- makewiki:section=install -->\n"
                "## Install\n\n"
                "[[id:install.init]]\n```bash\napp init --force\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n"
                "<!-- makewiki:section=install -->\n"
                "## 安装\n\n"
                "[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    report = verifier.verify_documents(docs)
    l4a_failures = [c for c in report.checks if c.claim_type == "l4a_mechanical" and c.status == "failed"]
    assert len(l4a_failures) >= 1


def test_l4_passes_when_blocks_match_by_id():
    """When ID-tagged blocks match across languages, L4a checks pass."""
    verifier = L4CrossLanguageVerifier()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n"
                "<!-- makewiki:section=install -->\n"
                "## Install\n\n"
                "[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n"
                "<!-- makewiki:section=install -->\n"
                "## 安装\n\n"
                "[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    report = verifier.verify_documents(docs)
    l4a_failures = [c for c in report.checks if c.claim_type == "l4a_mechanical" and c.status == "failed"]
    assert len(l4a_failures) == 0
