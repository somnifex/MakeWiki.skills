"""Integration test - verify output directory structure after assembly."""

import shutil
from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline

from tests.integration._helpers import seed_run_artifacts


def test_output_structure(minimal_python_cli_dir: Path, tmp_path: Path):
    """Verify the generated makewiki/ directory has the expected structure."""
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
    pipeline.run()

    wiki_dir = project_dir / "makewiki"
    assert wiki_dir.is_dir()

    assert (wiki_dir / "README.md").is_file()
    assert (wiki_dir / "getting-started.md").is_file()
    assert (wiki_dir / "installation.md").is_file()
    assert (wiki_dir / "configuration.md").is_file()
    assert (wiki_dir / "commands.md").is_file()
    assert (wiki_dir / "modules" / "overview.md").is_file()
    assert (wiki_dir / "modules" / "core.md").is_file()
    assert (wiki_dir / "workflows" / "overview.md").is_file()
    assert (wiki_dir / "workflows" / "hello-world.md").is_file()
    assert (wiki_dir / "integrations" / "overview.md").is_file()

    assert (wiki_dir / "README.zh-CN.md").is_file()
    assert (wiki_dir / "getting-started.zh-CN.md").is_file()
    assert (wiki_dir / "installation.zh-CN.md").is_file()
    assert (wiki_dir / "configuration.zh-CN.md").is_file()
    assert (wiki_dir / "commands.zh-CN.md").is_file()
    assert (wiki_dir / "modules" / "overview.zh-CN.md").is_file()
    assert (wiki_dir / "modules" / "core.zh-CN.md").is_file()
    assert (wiki_dir / "workflows" / "overview.zh-CN.md").is_file()
    assert (wiki_dir / "workflows" / "hello-world.zh-CN.md").is_file()

    assert not (wiki_dir / "index.md").exists()
    readme_content = (wiki_dir / "README.md").read_text(encoding="utf-8")
    assert "getting-started.md" in readme_content
    assert "README.zh-CN.md" in readme_content


def test_output_within_target_dir(minimal_python_cli_dir: Path, tmp_path: Path):
    """Verify output is always within <target>/makewiki/."""
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]
    seed_run_artifacts(
        project_dir,
        config,
        project_name="mini-cli",
        command="mini-cli hello --name World",
        entry_path="./src/myapp/main.py",
        include_integrations=False,
    )

    pipeline = Pipeline(config)
    ctx = pipeline.run()

    wiki_dir = project_dir / "makewiki"
    for fpath in ctx.written_files:
        assert Path(fpath).resolve().is_relative_to(wiki_dir.resolve())


def test_three_languages(minimal_python_cli_dir: Path, tmp_path: Path):
    """Verify that three languages produce correctly suffixed files."""
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN", "ja"]
    seed_run_artifacts(
        project_dir,
        config,
        project_name="mini-cli",
        command="mini-cli hello --name World",
        entry_path="./src/myapp/main.py",
        include_integrations=False,
    )

    pipeline = Pipeline(config)
    pipeline.run()

    wiki_dir = project_dir / "makewiki"
    assert (wiki_dir / "README.md").is_file()
    assert (wiki_dir / "README.zh-CN.md").is_file()
    assert (wiki_dir / "README.ja.md").is_file()
