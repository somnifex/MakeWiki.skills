"""Unit tests for revision early exit on no progress."""

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.pipeline.pipeline import PipelineContext, stage_revision
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry


def test_revision_stops_on_no_progress():
    """Verify that stage_revision stops immediately when no revision actions are taken."""
    config = MakeWikiConfig()
    config.revision.enabled = True
    config.revision.max_rounds = 3
    config.revision.stop_on_no_progress = True

    # A document with no errors or cliches
    docs = {
        "en": [
            GeneratedDocument(
                filename="README.md",
                base_name="README.md",
                language_code="en",
                content="# Clean Document\nNo issues here.",
            )
        ]
    }

    ctx = PipelineContext(
        config=config,
        generated_documents=docs,
        evidence_registry=EvidenceRegistry(),
    )

    result_ctx = stage_revision(ctx)

    # Since there are no issues, quality passes on check 1 or revise produces 0 actions
    assert result_ctx.revision_rounds <= 1
    assert result_ctx.final_documents["en"][0].content == "# Clean Document\nNo issues here."
