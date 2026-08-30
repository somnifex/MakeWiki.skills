"""Cognitive Authority Boundary contract.

This contract enforces the Two-Plane Architecture:
* Main Agent owns orchestration.
* Subagents own cognitive work (Scout, ReBattle, Language Writers, Auditor).
* Python owns NO scheduling, NO cognitive writing, and NO semantic repair.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.verification.l4_cross_language import (
    L4CrossLanguageVerifier,
    extract_blocks_by_id,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = PROJECT_ROOT / "SKILL.md"
SRC_DIR = PROJECT_ROOT / "src/makewiki_skills"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_repair_engine_and_generators_not_in_python():
    """Neither MechanicalRepairEngine nor LanguageGenerator exists in Python plane."""
    for py in SRC_DIR.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        assert "MechanicalRepairEngine" not in text
        assert "RevisionEngine" not in text
        assert "LegacyDeterministicRenderer" not in text


def test_authoritative_revision_loop_is_llm_auditor():
    """SKILL.md specifies that the revision loop is the LLM Auditor editing Markdown."""
    skill = _read(SKILL_MD)
    assert "MechanicalRepairEngine" not in skill
    assert "RevisionEngine" not in skill
    assert "Auditor edits Markdown in place" in skill


def test_stable_block_id_convention_enforced_by_l4():
    """L4 mechanical verifier extracts and enforces [[id:...]] block IDs."""
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
    deploy_full, deploy_hash = blocks["usage.deploy"]
    assert "make setup" in install_full
    assert "make deploy" in deploy_full


def test_l4_verifier_demands_stable_block_ids_on_technical_code():
    """Technical code blocks without stable IDs fail L4a mechanical verification."""
    verifier = L4CrossLanguageVerifier()
    docs = {
        "en": [
            DocumentArtifact(
                filename="README.md",
                base_name="README.md",
                language_code="en",
                content="# Welcome\n\n```bash\nmake install\n```\n",
            )
        ],
        "zh-CN": [
            DocumentArtifact(
                filename="README.zh-CN.md",
                base_name="README.md",
                language_code="zh-CN",
                content="# 欢迎\n\n```bash\nmake install\n```\n",
            )
        ],
    }
    report = verifier.verify_documents(docs)
    failures = [c for c in report.checks if c.claim_type == "l4a_mechanical" and c.status == "failed"]
    assert any("Untagged technical code block" in c.claim_text for c in failures)
