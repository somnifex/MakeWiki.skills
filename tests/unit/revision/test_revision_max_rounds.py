"""Unit tests for RevisionConfig.max_rounds constraint."""

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.pipeline.pipeline import PipelineContext, stage_revision
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry


def test_revision_respects_max_rounds():
    """Verify that stage_revision caps rounds at config.revision.max_rounds."""
    config = MakeWikiConfig()
    config.revision.enabled = True
    config.revision.max_rounds = 2
    config.revision.stop_on_no_progress = False

    # Document that has an issue that auto_hedge / auto_harmonize cannot fix (e.g. unknown config key)
    # causing quality_passed to remain False
    docs = {
        "en": [
            GeneratedDocument(
                filename="config.md",
                base_name="config.md",
                language_code="en",
                content="# Configuration\nUse `UNKNOWN_UNFIXABLE_CONFIG_KEY` to configure.",
            )
        ]
    }

    ctx = PipelineContext(
        config=config,
        generated_documents=docs,
        evidence_registry=EvidenceRegistry(),
    )

    result_ctx = stage_revision(ctx)

    # Must never exceed max_rounds = 2
    assert result_ctx.revision_rounds <= 2
    assert len(result_ctx.revision_reports) <= 2


def test_revision_disabled_returns_original_docs():
    """When revision is disabled, generated documents are passed through with 0 rounds."""
    config = MakeWikiConfig()
    config.revision.enabled = False

    docs = {
        "en": [
            GeneratedDocument(
                filename="README.md",
                base_name="README.md",
                language_code="en",
                content="# Doc\nContent",
            )
        ]
    }

    ctx = PipelineContext(
        config=config,
        generated_documents=docs,
    )

    result_ctx = stage_revision(ctx)
    assert result_ctx.revision_rounds == 0
    assert result_ctx.final_documents == docs
