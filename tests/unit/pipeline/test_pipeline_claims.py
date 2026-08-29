"""Unit tests for pipeline build_claims and verify_claims stages."""

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


def test_pipeline_runs_claim_stages_successfully(tmp_path: Path):
    config = MakeWikiConfig.default(tmp_path)
    pipeline = Pipeline(config)

    # Run up until verify_claims
    ctx = pipeline.run_until("verify_claims")

    assert ctx.detection is not None
    assert ctx.collected_evidence is not None
    assert ctx.claim_set is not None
    assert ctx.claim_set.project_name == ctx.detection.project_name
    assert isinstance(ctx.claim_set.claims, list)


def test_pipeline_claim_verification_state(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("# Test App\n```bash\npython app.py\n```", encoding="utf-8")

    config = MakeWikiConfig.default(tmp_path)
    pipeline = Pipeline(config)
    ctx = pipeline.run_until("verify_claims")

    assert ctx.claim_set is not None
    for claim in ctx.claim_set.claims:
        assert claim.verification.l0_syntax == "passed"
        assert claim.verification.l1_existence in ("passed", "failed")
