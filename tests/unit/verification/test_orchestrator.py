"""Unit tests for VerificationOrchestrator."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.orchestrator import VerificationOrchestrator


def test_orchestrator_runs_all_layers(tmp_path: Path):
    (tmp_path / "Makefile").write_text("build:\n\techo build\n", encoding="utf-8")

    doc_en = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# My Project\n\n## Build\n```bash\nmake build\n```\n",
    )
    doc_zh = GeneratedDocument(
        filename="README.zh-CN.md",
        base_name="README.md",
        language_code="zh-CN",
        content="# 项目名称\n\n## 构建\n```bash\nmake build\n```\n",
    )

    orchestrator = VerificationOrchestrator(tmp_path)
    report = orchestrator.verify_documents({"en": [doc_en], "zh-CN": [doc_zh]})

    assert len(report.layers) == 6
    assert set(report.layers.keys()) == {"L0", "L1", "L2", "L3", "L4", "L5"}
    assert report.passed
    # No layer may be falsely "passed": the LLM-judged / vacuous L3/L4/L5 layers
    # report pending checks that do not count toward the score, so the aggregate
    # score is honest (below 1.0) rather than inflated to a vacuous 1.0.
    assert report.score < 1.0


def test_orchestrator_verify_single_layer(tmp_path: Path):
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# Title\n\n## Section\nContent",
    )
    orchestrator = VerificationOrchestrator(tmp_path)
    l0_report = orchestrator.verify_layer("L0", {"en": [doc]})

    assert l0_report.layer == "L0"
    assert l0_report.passed
