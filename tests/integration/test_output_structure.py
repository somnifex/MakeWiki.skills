"""Integration test - verify output directory structure after full pipeline run."""

import shutil
from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline


def test_output_structure(minimal_python_cli_dir: Path, tmp_path: Path):
    """Verify the generated makewiki/ directory has the expected structure."""
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN"]

    pipeline = Pipeline(config)
    pipeline.run()

    wiki_dir = project_dir / "makewiki"
    assert wiki_dir.is_dir()

    # English files (default, no suffix)
    assert (wiki_dir / "README.md").is_file()
    assert (wiki_dir / "getting-started.md").is_file()
    assert (wiki_dir / "installation.md").is_file()
    assert (wiki_dir / "configuration.md").is_file()
    assert (wiki_dir / "usage" / "basic-usage.md").is_file()

    # Chinese files (with .zh-CN suffix)
    assert (wiki_dir / "README.zh-CN.md").is_file()
    assert (wiki_dir / "getting-started.zh-CN.md").is_file()
    assert (wiki_dir / "installation.zh-CN.md").is_file()
    assert (wiki_dir / "configuration.zh-CN.md").is_file()
    assert (wiki_dir / "usage" / "basic-usage.zh-CN.md").is_file()

    # Index file
    assert (wiki_dir / "index.md").is_file()
    index_content = (wiki_dir / "index.md").read_text(encoding="utf-8")
    assert "en" in index_content or "README.md" in index_content
    assert "zh-CN" in index_content or "README.zh-CN.md" in index_content


def test_output_within_target_dir(minimal_python_cli_dir: Path, tmp_path: Path):
    """Verify output is always within <target>/makewiki/."""
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]

    pipeline = Pipeline(config)
    ctx = pipeline.run()

    # All written files should be under project_dir / makewiki
    wiki_dir = project_dir / "makewiki"
    for fpath in ctx.written_files:
        assert Path(fpath).resolve().is_relative_to(wiki_dir.resolve())


def test_three_languages(minimal_python_cli_dir: Path, tmp_path: Path):
    """Verify that three languages produce correctly suffixed files."""
    project_dir = tmp_path / "project"
    shutil.copytree(minimal_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN", "ja"]

    pipeline = Pipeline(config)
    pipeline.run()

    wiki_dir = project_dir / "makewiki"
    assert (wiki_dir / "README.md").is_file()
    assert (wiki_dir / "README.zh-CN.md").is_file()
    assert (wiki_dir / "README.ja.md").is_file()
