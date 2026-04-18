"""Integration test - full pipeline on the minimal-python-cli fixture."""

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline


def test_full_pipeline_python_cli(minimal_python_cli_dir: Path, tmp_path: Path):
    """Run the full 7-stage pipeline on a minimal Python CLI project."""
    # Copy fixture to tmp_path so we don't pollute the repo
    import shutil
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN"]

    pipeline = Pipeline(config)
    ctx = pipeline.run()

    # No fatal errors
    assert not ctx.errors, f"Pipeline errors: {ctx.errors}"

    # Detection succeeded
    assert ctx.detection is not None
    assert ctx.detection.project_name == "mini-cli"

    # Evidence collected
    assert len(ctx.evidence_registry) > 0

    # Semantic model built
    assert ctx.semantic_model is not None
    assert ctx.semantic_model.identity.name == "mini-cli"

    # Documents generated for both languages
    assert "en" in ctx.generated_documents
    assert "zh-CN" in ctx.generated_documents
    assert len(ctx.generated_documents["en"]) >= 5
    assert len(ctx.generated_documents["zh-CN"]) >= 5

    # Cross-language review ran
    assert ctx.cross_language_review is not None

    # Grounding verification ran
    assert ctx.grounding_report is not None

    # Files written
    assert len(ctx.written_files) > 0
    wiki_dir = project_dir / "makewiki"
    assert wiki_dir.is_dir()
    assert (wiki_dir / "README.md").is_file()
    assert (wiki_dir / "README.zh-CN.md").is_file()


def test_pipeline_scan_only(minimal_python_cli_dir: Path):
    """Run only stages 1-2 (detect + collect evidence)."""
    config = MakeWikiConfig.default(minimal_python_cli_dir)
    pipeline = Pipeline(config)
    ctx = pipeline.run_until("collect_evidence")

    assert ctx.detection is not None
    assert ctx.collected_evidence is not None
    assert len(ctx.evidence_registry) > 0
    # No documents generated
    assert len(ctx.generated_documents) == 0
