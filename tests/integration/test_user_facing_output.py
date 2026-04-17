"""Integration tests for user-facing output defaults."""

import shutil
from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline

from tests.integration._helpers import seed_run_artifacts


def test_sample_output_stays_user_facing(sample_python_cli_dir: Path, tmp_path: Path):
    project_dir = tmp_path / "project"
    shutil.copytree(sample_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]
    seed_run_artifacts(
        project_dir,
        config,
        project_name="sample-cli",
        command="sample-cli greet World",
        entry_path="./src/sample/cli.py",
        config_key="SERVER_PORT",
        include_integrations=True,
    )

    ctx = Pipeline(config).run()
    assert not ctx.errors

    wiki_dir = project_dir / "makewiki"
    readme = (wiki_dir / "README.md").read_text(encoding="utf-8")
    commands = (wiki_dir / "commands.md").read_text(encoding="utf-8")
    configuration = (wiki_dir / "configuration.md").read_text(encoding="utf-8")
    module_page = (wiki_dir / "modules" / "core.md").read_text(encoding="utf-8")

    assert "## Commands" not in readme
    assert "architecture" not in readme.lower()
    assert "sample-cli greet World" in commands
    assert "SERVER_PORT" in configuration
    assert "[^low-1]" in configuration
    assert "Inferred by fallback scan from `src/sample/cli.py`." in configuration
    assert "./src/sample/cli.py" in module_page
