"""Unit tests for RevisionEngine."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReview, FactDelta
from makewiki_skills.revision.revision_engine import RevisionEngine
from makewiki_skills.verification.code_grounding_verifier import (
    GroundingClaim,
    GroundingReport,
    GroundingViolation,
)
from makewiki_skills.verification.codebase_verifier import (
    CodebaseCheck,
    CodebaseVerificationReport,
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


def test_revision_engine_hedging_from_codebase_report():
    engine = RevisionEngine(auto_hedge=True)
    docs = {
        "zh-CN": [
            GeneratedDocument(
                filename="usage.zh-CN.md",
                base_name="usage.md",
                language_code="zh-CN",
                content="执行命令：\n```bash\nmyapp start --unknown\n```",
            )
        ]
    }
    codebase_report = CodebaseVerificationReport(
        checks=[
            CodebaseCheck(
                document="usage.zh-CN.md",
                language_code="zh-CN",
                claim_text="myapp start --unknown",
                claim_type="command",
                verified=False,
                detail="not found",
            )
        ]
    )
    revised, report = engine.revise(docs, codebase_report=codebase_report)
    assert report.total_actions > 0
    content = revised["zh-CN"][0].content
    assert "[!NOTE]" in content
    assert "未找到显式 AST 声明" in content


def test_revision_engine_harmonize_code_blocks():
    engine = RevisionEngine(auto_harmonize=True)
    docs = {
        "en": [
            GeneratedDocument(
                filename="README.md",
                base_name="README.md",
                language_code="en",
                content="# Welcome\n\n```bash\nmyapp init\n```\n\n```bash\nmyapp build\n```",
            )
        ],
        "zh-CN": [
            GeneratedDocument(
                filename="README.zh-CN.md",
                base_name="README.md",
                language_code="zh-CN",
                content="# 欢迎\n\n```bash\nmyapp init\n```",
            )
        ],
    }
    cross_report = CrossLanguageReview(
        languages_reviewed=["en", "zh-CN"],
        fact_deltas=[
            FactDelta(
                fact_type="command",
                value="myapp build",
                present_in=["en"],
                missing_from=["zh-CN"],
                severity="critical",
            )
        ],
    )
    revised, report = engine.revise(docs, cross_language_report=cross_report)
    assert any(a.action_type == "harmonize_code_block" for a in report.actions)
    assert "myapp build" in revised["zh-CN"][0].content


def test_revision_engine_clean_documents_no_actions():
    engine = RevisionEngine()
    docs = {
        "en": [
            GeneratedDocument(
                filename="README.md",
                base_name="README.md",
                language_code="en",
                content="# Welcome\nClean documentation content with no issues.",
            )
        ]
    }
    revised, report = engine.revise(docs)
    assert report.total_actions == 0
    assert len(report.actions) == 0
