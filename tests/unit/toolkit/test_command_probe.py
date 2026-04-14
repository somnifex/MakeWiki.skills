"""Tests for CommandProbeTool."""

from pathlib import Path

from makewiki_skills.toolkit.command_probe import CommandProbeTool


def test_parse_makefile(tmp_path: Path):
    makefile = tmp_path / "Makefile"
    makefile.write_text(
        ".PHONY: test lint\n\ntest: ## Run tests\n\tpytest tests/\n\nlint: ## Lint code\n\truff check .\n",
        encoding="utf-8",
    )

    tool = CommandProbeTool()
    result = tool.parse_makefile(makefile)
    assert result.success
    targets = result.data["targets"]
    names = [t["name"] for t in targets]
    assert "test" in names
    assert "lint" in names
    # Check description parsing
    test_target = next(t for t in targets if t["name"] == "test")
    assert test_target["description"] == "Run tests"


def test_parse_package_json_scripts(tmp_path: Path):
    pkg = tmp_path / "package.json"
    pkg.write_text(
        '{"name": "app", "scripts": {"dev": "vite", "build": "tsc && vite build", "test": "vitest"}}',
        encoding="utf-8",
    )

    tool = CommandProbeTool()
    result = tool.parse_package_json_scripts(pkg)
    assert result.success
    scripts = result.data["scripts"]
    names = [s["name"] for s in scripts]
    assert "dev" in names
    assert "build" in names
    assert "test" in names


def test_parse_pyproject_scripts(tmp_path: Path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "hello"\n\n[project.scripts]\nmycli = "myapp.main:app"\n',
        encoding="utf-8",
    )

    tool = CommandProbeTool()
    result = tool.parse_pyproject_scripts(pyproject)
    assert result.success
    scripts = result.data["scripts"]
    assert len(scripts) == 1
    assert scripts[0]["name"] == "mycli"


def test_detect_available_commands(tmp_path: Path):
    # Create a Makefile and a pyproject.toml
    (tmp_path / "Makefile").write_text("test:\n\tpytest\n", encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "x"\n\n[project.scripts]\nmytool = "x:main"\n',
        encoding="utf-8",
    )

    tool = CommandProbeTool()
    result = tool.detect_available_commands(tmp_path)
    assert result.success
    commands = result.data["commands"]
    cmd_names = [c["name"] for c in commands]
    assert "make test" in cmd_names
    assert "mytool" in cmd_names


def test_parse_nonexistent_file(tmp_path: Path):
    tool = CommandProbeTool()
    result = tool.parse_makefile(tmp_path / "Makefile")
    assert not result.success
