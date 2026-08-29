"""Integration tests for user-facing output defaults."""

import shutil
from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline


def test_sample_output_stays_user_facing(sample_python_cli_dir: Path, tmp_path: Path):
    project_dir = tmp_path / "project"
    shutil.copytree(sample_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]

    ctx = Pipeline(config).run()
    assert not ctx.errors

    wiki_dir = project_dir / "makewiki"
    readme = (wiki_dir / "README.md").read_text(encoding="utf-8")
    usage = (wiki_dir / "usage" / "basic-usage.md").read_text(encoding="utf-8")
    configuration = (wiki_dir / "configuration.md").read_text(encoding="utf-8")

    assert "## Commands" not in readme
    assert "Documentation Navigation" in readme
    # Python must never invent usage examples — it emits an UNKNOWN marker instead.
    assert "make test" not in usage
    assert "make lint" not in usage
    assert "sample-cli greet World" not in usage
    assert "No repeatable usage patterns" in usage
    assert "pyproject.toml" not in configuration
    assert ".env.example" in configuration
