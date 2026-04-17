"""Integration test - artifact-first pipeline on the minimal-python-cli fixture."""

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline

from tests.integration._helpers import seed_run_artifacts


def test_full_pipeline_python_cli(minimal_python_cli_dir: Path, tmp_path: Path):
    """Run the artifact-first pipeline with pre-seeded LLM artifacts."""
    import shutil
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN"]
    seed_run_artifacts(
        project_dir,
        config,
        project_name="mini-cli",
        command="mini-cli hello --name World",
        entry_path="./src/myapp/main.py",
        include_integrations=True,
    )

    pipeline = Pipeline(config)
    ctx = pipeline.run()

    assert not ctx.errors, f"Pipeline errors: {ctx.errors}"
    assert ctx.detection is not None
    assert ctx.detection.project_name == "mini-cli"
    assert len(ctx.evidence_registry) > 0
    assert ctx.run_layout is not None
    assert ctx.semantic_index is not None
    assert "en" in ctx.generated_documents
    assert "zh-CN" in ctx.generated_documents
    assert len(ctx.generated_documents["en"]) >= 8
    assert len(ctx.generated_documents["zh-CN"]) >= 8
    assert ctx.cross_language_review is not None
    assert ctx.grounding_report is not None
    assert ctx.codebase_verification_report is not None
    assert len(ctx.written_files) > 0
    wiki_dir = project_dir / "makewiki"
    assert wiki_dir.is_dir()
    assert (wiki_dir / "README.md").is_file()
    assert (wiki_dir / "README.zh-CN.md").is_file()
    assert (wiki_dir / "modules" / "core.md").is_file()
    assert (wiki_dir / "workflows" / "hello-world.md").is_file()
    assert (wiki_dir / "integrations" / "overview.md").is_file()


def test_pipeline_scan_only(minimal_python_cli_dir: Path):
    """Run only stages 1-2 (detect + collect evidence)."""
    config = MakeWikiConfig.default(minimal_python_cli_dir)
    pipeline = Pipeline(config)
    ctx = pipeline.run_until("collect_evidence")

    assert ctx.detection is not None
    assert ctx.collected_evidence is not None
    assert len(ctx.evidence_registry) > 0
    assert len(ctx.generated_documents) == 0
