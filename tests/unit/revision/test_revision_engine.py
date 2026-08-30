"""Unit tests for MechanicalRepairEngine.

The engine performs MECHANICAL repairs only. Semantic prose rewriting
(anti-cliché) is NOT part of the normal repair loop — it lives behind the
explicit ``legacy_anti_cliche=True`` scaffold flag.
"""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReview, FactDelta
from makewiki_skills.revision.revision_engine import MechanicalRepairEngine
from makewiki_skills.verification.code_grounding_verifier import (
    GroundingClaim,
    GroundingReport,
    GroundingViolation,
)
from makewiki_skills.verification.codebase_verifier import (
    CodebaseCheck,
    CodebaseVerificationReport,
)


def _doc(filename: str, base_name: str, language_code: str, content: str) -> GeneratedDocument:
    return GeneratedDocument(
        filename=filename,
        base_name=base_name,
        language_code=language_code,
        content=content,
    )


def test_mechanical_repair_engine_does_not_rewrite_prose():
    """The normal repair loop must NOT apply anti-cliché / semantic prose edits."""
    engine = MechanicalRepairEngine()
    docs = {
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "## 步骤 1：安装依赖\nMakeWiki 不仅是一个文档工具，更是为一个静态网站生成器。",
            )
        ]
    }
    revised, report = engine.revise(docs)
    # No semantic prose actions on a clean(with-respect-to-mechanics) document.
    assert all(a.action_type != "format_normalize" for a in report.actions)
    # The colon and cliché phrasing are left untouched by the mechanical loop.
    assert "## 步骤 1：安装依赖" in revised["zh-CN"][0].content
    assert "不仅是一个文档工具" in revised["zh-CN"][0].content


def test_legacy_anti_cliche_cleanup_only_with_flag():
    """The legacy anti-cliché cleanup runs ONLY under ``legacy_anti_cliche=True``."""
    docs = {
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "## 步骤 1：安装依赖\nMakeWiki 不仅是一个文档工具，更是为一个静态网站生成器。提供赋能与底层逻辑。",
            )
        ]
    }

    # Default: flag off -> no rewrite.
    engine = MechanicalRepairEngine()
    revised, report = engine.revise(docs)
    assert report.total_actions == 0
    assert "## 步骤 1：安装依赖" in revised["zh-CN"][0].content

    # Flag on -> legacy scaffold cleanup applies.
    legacy_engine = MechanicalRepairEngine(legacy_anti_cliche=True)
    legacy_revised, legacy_report = legacy_engine.revise(docs)
    assert legacy_report.total_actions > 0
    content = legacy_revised["zh-CN"][0].content
    assert "## 步骤 1 安装依赖" in content
    assert "核心机制" in content or "支持" in content


def test_mechanical_repair_engine_hedging_ungrounded_command():
    engine = MechanicalRepairEngine(auto_hedge=True)
    docs = {
        "en": [
            _doc(
                "usage.md",
                "usage.md",
                "en",
                "Run the following:\n```bash\nmyapp run --fake-flag\n```\nDone.",
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
    assert any(a.action_type == "hedge_ungrounded" for a in report.actions)
    assert "[!NOTE]" in revised["en"][0].content
    # Canned UNKNOWN evidence marker — no invented "may be experimental" prose.
    assert "could not be mechanically verified against the codebase" in revised["en"][0].content
    assert "may be experimental" not in revised["en"][0].content


def test_mechanical_repair_engine_hedging_from_codebase_report():
    engine = MechanicalRepairEngine(auto_hedge=True)
    docs = {
        "zh-CN": [
            _doc(
                "usage.zh-CN.md",
                "usage.md",
                "zh-CN",
                "执行命令：\n```bash\nmyapp start --unknown\n```",
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
    # Single canonical English UNKNOWN evidence marker — Python does not
    # translate narrative; localization is the LLM Auditor/Writer's job.
    assert "could not be mechanically verified against the codebase" in content
    assert "无法机械验证" not in content


def test_mechanical_repair_engine_harmonize_by_stable_id():
    """Code blocks are harmonized by stable [[id:...]] marker, not position."""
    engine = MechanicalRepairEngine(auto_harmonize=True)
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n[[id:install.init]]\n```bash\nmyapp init\n```\n\n"
                "[[id:install.build]]\n```bash\nmyapp build\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n[[id:install.init]]\n```bash\nmyapp init\n```\n",
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
    # The missing build block (keyed by its stable ID) is appended to zh.
    assert "myapp build" in revised["zh-CN"][0].content
    # The existing init block was NOT duplicated.
    assert revised["zh-CN"][0].content.count("myapp init") == 1


def test_mechanical_repair_engine_harmonizes_diverged_block_by_id():
    """A block sharing an ID but differing in body is replaced byte-exactly."""
    engine = MechanicalRepairEngine(auto_harmonize=True)
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\n\n[[id:install.init]]\n```bash\nmyapp init --force\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# 欢迎\n\n[[id:install.init]]\n```bash\nmyapp init\n```\n",
            )
        ],
    }
    cross_report = CrossLanguageReview(languages_reviewed=["en", "zh-CN"])
    revised, report = engine.revise(docs, cross_language_report=cross_report)
    assert any(a.action_type == "harmonize_code_block" for a in report.actions)
    content = revised["zh-CN"][0].content
    assert "myapp init --force" in content
    assert "myapp init\n" not in content.replace("myapp init --force", "")


def test_mechanical_repair_engine_clean_documents_no_actions():
    engine = MechanicalRepairEngine()
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# Welcome\nClean documentation content with no issues.",
            )
        ]
    }
    revised, report = engine.revise(docs)
    assert report.total_actions == 0
    assert len(report.actions) == 0


def test_harmonizer_does_not_silently_skip_untagged_technical_block():
    """An untagged technical fence records a warning instead of being silently
    skipped; ID-tagged block behavior is unchanged."""
    engine = MechanicalRepairEngine(auto_harmonize=True)
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# T\n[[id:init]]\n```bash\napp init\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# T\n[[id:init]]\n```bash\napp init\n```\n\n"
                "```bash\napp untagged\n```\n",
            )
        ],
    }
    cross_report = CrossLanguageReview(languages_reviewed=["en", "zh-CN"])
    revised, report = engine.revise(docs, cross_language_report=cross_report)

    # The untagged technical fence surfaced a warning (not silently dropped).
    assert any("untagged technical fence" in w for w in report.warnings)
    assert any("zh-CN" in w and "README.md" in w for w in report.warnings)
    # Tagged-block harmonization behavior is unchanged.
    assert "app init" in revised["zh-CN"][0].content
    # The untagged fence is left intact (never repaired to a silent no-op).
    assert "app untagged" in revised["zh-CN"][0].content


def test_tagged_block_independent_no_warning():
    """A fully tagged, consistent pair produces no untagged warning."""
    engine = MechanicalRepairEngine(auto_harmonize=True)
    docs = {
        "en": [
            _doc(
                "README.md",
                "README.md",
                "en",
                "# T\n[[id:init]]\n```bash\napp init\n```\n",
            )
        ],
        "zh-CN": [
            _doc(
                "README.zh-CN.md",
                "README.md",
                "zh-CN",
                "# T\n[[id:init]]\n```bash\napp init\n```\n",
            )
        ],
    }
    cross_report = CrossLanguageReview(languages_reviewed=["en", "zh-CN"])
    revised, report = engine.revise(docs, cross_language_report=cross_report)
    assert report.warnings == []

