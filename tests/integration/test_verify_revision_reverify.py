"""Integration test: closed-loop verify -> revision -> reverify workflow."""

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.model.document_artifact import GeneratedDocument
from makewiki_skills.pipeline.pipeline import (
    PipelineContext,
    count_issues,
    quality_passed,
    stage_revision,
)
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.verification.code_grounding_verifier import CodeGroundingVerifier
from makewiki_skills.verification.codebase_verifier import CodebaseVerifier


def test_verify_revision_reverify_loop(tmp_path: Path):
    """Closed-loop test:

    1. Construct document with an ungrounded command.
    2. First verifiers detect error (grounding violation + codebase failure).
    3. Revision engine fixes it (attaches hedging note).
    4. Second verifiers confirm error is resolved and pass.
    """
    config = MakeWikiConfig.default(tmp_path)
    config.revision.enabled = True
    config.revision.max_rounds = 2
    config.revision.auto_hedge_ungrounded = True
    config.strict_grounding = True

    # Empty registry so the custom command has no evidence
    registry = EvidenceRegistry()

    bad_command = "myapp run --nonexistent-option"
    initial_docs = {
        "en": [
            GeneratedDocument(
                filename="usage.md",
                base_name="usage.md",
                language_code="en",
                content=f"# Usage\n\nRun the following command:\n```bash\n{bad_command}\n```\n",
            )
        ]
    }

    # Step 1: Initial verification - must fail
    grounding_verifier = CodeGroundingVerifier(registry, strict=True)
    initial_grounding = grounding_verifier.verify(initial_docs)
    assert len(initial_grounding.violations) == 1
    assert initial_grounding.violations[0].claim.claim_text == bad_command

    codebase_verifier = CodebaseVerifier(tmp_path)
    initial_codebase = codebase_verifier.verify(initial_docs)
    assert initial_codebase.failed_count == 1

    assert not quality_passed(None, initial_grounding, initial_codebase, config)
    expected_issues_before = count_issues(None, initial_grounding, initial_codebase)
    assert expected_issues_before == 2

    # Step 2: Run stage_revision
    ctx = PipelineContext(
        config=config,
        generated_documents=initial_docs,
        evidence_registry=registry,
    )
    result_ctx = stage_revision(ctx)

    # Step 3: Check revision metrics
    assert result_ctx.revision_rounds >= 1
    assert len(result_ctx.revision_reports) >= 1
    report = result_ctx.revision_reports[0]
    assert report.total_actions > 0
    assert report.issues_before == expected_issues_before
    assert report.issues_after == 0
    assert report.verified_resolutions == expected_issues_before

    # Step 4: Re-verification on final documents - must pass
    final_grounding = grounding_verifier.verify(result_ctx.final_documents)
    assert len(final_grounding.violations) == 0
    assert final_grounding.grounding_score == 1.0

    final_codebase = codebase_verifier.verify(result_ctx.final_documents)
    assert final_codebase.failed_count == 0

    assert quality_passed(None, final_grounding, final_codebase, config)
