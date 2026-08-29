"""Unit tests for RevisionEngine."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.revision.revision_engine import RevisionEngine
from makewiki_skills.verification.code_grounding_verifier import (
    GroundingClaim,
    GroundingReport,
    GroundingViolation,
)


def test_revision_engine_anti_cliche_sanitization():
    engine = RevisionEngine()
    docs = {
        "zh-CN": [
            GeneratedDocument(
                filename="README.zh-CN.md",
                base_name="README.md",
                language_code="zh-CN",
                content="## 步骤 1：安装依赖\nMakeWiki 不仅是一个文档工具，更是为一个静态网站生成器。不是简单的工具，而是高效编译器。提供赋能与底层逻辑。",
            )
        ]
    }
    revised, report = engine.revise(docs)
    assert report.total_actions > 0
    content = revised["zh-CN"][0].content
    assert "## 步骤 1 安装依赖" in content
    assert "不是" not in content or "高效编译器" in content
    assert "核心机制" in content or "支持" in content


def test_revision_engine_hedging_ungrounded_command():
    engine = RevisionEngine(auto_hedge=True)
    docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content="Run the following:\n```bash\nmyapp run --fake-flag\n```\nDone.",
            )
        ]
    }
    grounding_report = GroundingReport(
        violations=[
            GroundingViolation(
                claim=GroundingClaim(
                    document="usage.md",
                    language_code="en",
                    claim_text="myapp run --fake-flag",
                    claim_type="command",
                ),
                violation_type="ungrounded",
                message="Ungrounded command",
            )
        ]
    )
    revised, report = engine.revise(docs, grounding_report=grounding_report)
    assert report.total_actions > 0
    assert "[!NOTE]" in revised["en"][0].content
    assert "inferred from configuration" in revised["en"][0].content
