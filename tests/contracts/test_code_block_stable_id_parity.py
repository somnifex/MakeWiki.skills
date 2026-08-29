"""Stable code-block ID parity contract.

Cross-language code-block parity must match logical blocks by a stable
``[[id:...]]`` marker — never by position. This contract verifies the
mechanical harmonizer:

* extracts blocks keyed by their stable ID,
* compares block bodies by content hash,
* appends ID-tagged blocks that are missing from a secondary language, and
* replaces ID-tagged blocks whose body diverged from the primary (byte-exact).

Blocks without an ID marker are intentionally NOT positionally harmonized —
without a stable ID, Python cannot prove they are the same logical block.
"""

from __future__ import annotations

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.revision.revision_engine import MechanicalRepairEngine

ID_PATTERN = r"[[id:{id}]]"
BLOCK_ID_MARKER = "[[id:getting_started.install]]"


def _doc(filename: str, base_name: str, language_code: str, content: str) -> GeneratedDocument:
    return GeneratedDocument(
        filename=filename,
        base_name=base_name,
        language_code=language_code,
        content=content,
    )


def test_extract_blocks_keyed_by_stable_id():
    content = (
        "# Doc\n\n"
        "[[id:getting_started.install]]\n```bash\nmake setup\n```\n\n"
        "[[id:usage.deploy]]\n```bash\nmake deploy\n```\n"
    )
    blocks = MechanicalRepairEngine._extract_blocks_by_id(content)
    assert set(blocks.keys()) == {"getting_started.install", "usage.deploy"}
    install_block, install_hash = blocks["getting_started.install"]
    assert "make setup" in install_block
    assert isinstance(install_hash, str) and len(install_hash) == 16


def test_content_hash_differs_for_different_bodies():
    engine = MechanicalRepairEngine()
    a = engine._content_hash("make setup\n")
    b = engine._content_hash("make setup --force\n")
    assert a != b
    # Deterministic and stable in length.
    assert engine._content_hash("make setup\n") == a


def test_harmonize_appends_missing_block_by_id_not_position():
    """A block missing from the secondary is appended by its stable ID."""
    engine = MechanicalRepairEngine()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n"
                "[[id:install.init]]\n```bash\napp init\n```\n\n"
                "[[id:install.build]]\n```bash\napp build\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    harmonized = engine._harmonize_cross_language_code(docs)
    assert harmonized >= 1
    content = docs["zh-CN"][0].content
    # The missing ID-tagged build block is appended.
    assert "app build" in content
    # The existing init block is not duplicated by position.
    assert content.count("app init") == 1


def test_harmonize_replaces_diverged_block_by_id():
    """A block sharing an ID but differing in body is replaced byte-exactly."""
    engine = MechanicalRepairEngine()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n[[id:install.init]]\n```bash\napp init --force\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n[[id:install.init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    engine._harmonize_cross_language_code(docs)
    content = docs["zh-CN"][0].content
    assert "app init --force" in content
    # The diverged body is replaced, not appended redundantly.
    assert content.count("[[id:install.init]]") == 1


def test_unid_blocks_are_not_harmonized_by_position():
    """Without a stable ID, parity cannot be proven and nothing is harmonized."""
    engine = MechanicalRepairEngine()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n```bash\napp build\n```\n\n```bash\napp deploy\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n```bash\napp build\n```\n",
            )
        ],
    }
    harmonized = engine._harmonize_cross_language_code(docs)
    assert harmonized == 0
    # The second positional block is NOT appended, since no ID proves identity.
    assert "app deploy" not in docs["zh-CN"][0].content


def test_id_marker_inside_fence_body_is_recognized():
    """The ID marker may also be the first line inside the fence body."""
    engine = MechanicalRepairEngine()
    # Odd real-world form: marker as a fence-internal first line.
    assert engine._block_id("```bash\n[[id:install.init]]\napp init\n```") == "install.init"
