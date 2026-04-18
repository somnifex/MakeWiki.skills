"""Tests for _is_detailed_mode and _build_command_groups enhancements."""

from __future__ import annotations

from makewiki_skills.model.semantic_model import (
    Command,
    ConfigItem,
    ConfigSection,
    UserTask,
    UsageExample,
)
from makewiki_skills.pipeline.pipeline import _build_command_groups, _is_detailed_mode


# --- _is_detailed_mode tests ---


def test_detailed_mode_explicit_detailed():
    assert _is_detailed_mode("detailed", [], [], []) is True


def test_detailed_mode_explicit_compact():
    cmds = [Command(name=f"cmd{i}") for i in range(20)]
    assert _is_detailed_mode("compact", cmds, [], []) is False


def test_detailed_mode_auto_simple():
    """Few commands, few config, few tasks -> not detailed."""
    cmds = [Command(name=f"cmd{i}") for i in range(3)]
    cfg = [ConfigSection(name="main", items=[ConfigItem(key=f"k{i}") for i in range(4)])]
    tasks = [UserTask(title=f"task{i}") for i in range(2)]
    assert _is_detailed_mode("auto", cmds, cfg, tasks) is False


def test_detailed_mode_auto_complex_multi_dimension():
    """Two dimensions exceed thresholds -> detailed."""
    cmds = [Command(name=f"cmd{i}") for i in range(6)]  # >= 5
    cfg = [ConfigSection(name="main", items=[ConfigItem(key=f"k{i}") for i in range(12)])]  # >= 10
    tasks = [UserTask(title=f"task{i}") for i in range(3)]  # < 8
    assert _is_detailed_mode("auto", cmds, cfg, tasks) is True


def test_detailed_mode_auto_one_dimension_not_enough():
    """Only one dimension exceeds threshold -> not detailed (unless total is high)."""
    cmds = [Command(name=f"cmd{i}") for i in range(7)]  # >= 5
    cfg = [ConfigSection(name="main", items=[ConfigItem(key=f"k{i}") for i in range(3)])]  # < 10
    tasks = [UserTask(title=f"task{i}") for i in range(2)]  # < 8
    # total = 7+3+2 = 12, < 15
    assert _is_detailed_mode("auto", cmds, cfg, tasks) is False


def test_detailed_mode_auto_high_total():
    """Total >= 15 triggers detailed even if individual thresholds aren't exceeded."""
    cmds = [Command(name=f"cmd{i}") for i in range(4)]  # < 5
    cfg = [ConfigSection(name="main", items=[ConfigItem(key=f"k{i}") for i in range(7)])]  # < 10
    tasks = [UserTask(title=f"task{i}") for i in range(5)]  # < 8
    # total = 4+7+5 = 16, >= 15
    assert _is_detailed_mode("auto", cmds, cfg, tasks) is True


# --- _build_command_groups tests ---


def _make_commands_from_sources(sources: dict[str, int]) -> list[Command]:
    """Helper: create commands grouped by source file."""
    commands = []
    for source, count in sources.items():
        for i in range(count):
            commands.append(Command(name=f"{source}-cmd-{i}", source_file=source))
    return commands


def test_build_groups_simple_not_detailed():
    """Not detailed -> empty groups."""
    cmds = _make_commands_from_sources({"README.md": 3, "Makefile": 3})
    groups = _build_command_groups(cmds, [], [], 6, False)
    assert groups == []


def test_build_groups_below_threshold():
    """Below split threshold -> empty groups."""
    cmds = _make_commands_from_sources({"README.md": 2, "Makefile": 2})
    groups = _build_command_groups(cmds, [], [], 6, True)
    assert groups == []


def test_build_groups_single_source():
    """Single source file -> no splitting."""
    cmds = _make_commands_from_sources({"README.md": 8})
    groups = _build_command_groups(cmds, [], [], 6, True)
    assert groups == []


def test_build_groups_multiple_sources():
    """Multiple sources above threshold -> groups created."""
    cmds = _make_commands_from_sources({"README.md": 4, "Makefile": 4})
    groups = _build_command_groups(cmds, [], [], 6, True)
    assert len(groups) == 2
    slugs = {g.slug for g in groups}
    assert "readme" in slugs
    assert "makefile" in slugs


def test_build_groups_config_association():
    """Config sections are associated with groups via task.related_config."""
    cmds = [
        Command(name="serve --port 8080", source_file="README.md"),
        Command(name="make serve", source_file="README.md"),
        Command(name="make serve", source_file="Makefile"),
        Command(name="make build", source_file="Makefile"),
        Command(name="make deploy", source_file="Makefile"),
        Command(name="make test", source_file="Makefile"),
    ]
    tasks = [
        UserTask(
            title="Start the application",
            commands=["serve --port 8080"],
            related_config=["PORT", "HOST"],
        ),
    ]
    config = [
        ConfigSection(
            name="Server",
            items=[ConfigItem(key="PORT"), ConfigItem(key="HOST")],
        ),
        ConfigSection(
            name="Database",
            items=[ConfigItem(key="DB_URL")],
        ),
    ]
    groups = _build_command_groups(cmds, tasks, [], 6, True, configuration=config)

    assert len(groups) == 2
    readme_group = next(g for g in groups if g.slug == "readme")
    # The "serve --port 8080" command matches the task, which has related_config PORT/HOST
    assert len(readme_group.config_sections) == 1
    assert readme_group.config_sections[0].name == "Server"


def test_build_groups_description_from_tasks():
    """Groups get descriptions generated from their tasks."""
    cmds = [
        Command(name="serve --port 8080", source_file="README.md"),
        Command(name="make serve", source_file="README.md"),
        Command(name="make serve", source_file="Makefile"),
        Command(name="make build", source_file="Makefile"),
        Command(name="make deploy", source_file="Makefile"),
        Command(name="make test", source_file="Makefile"),
    ]
    tasks = [
        UserTask(
            title="Start the application",
            user_goal="Run the project locally.",
            commands=["serve --port 8080"],
        ),
    ]
    groups = _build_command_groups(cmds, tasks, [], 6, True)

    readme_group = next(g for g in groups if g.slug == "readme")
    assert readme_group.description is not None
    assert "Run the project locally" in readme_group.description


def test_build_groups_ungrouped_commands():
    """Commands without source_file go into a General group."""
    cmds = [
        Command(name="cmd1", source_file="README.md"),
        Command(name="cmd2", source_file="README.md"),
        Command(name="cmd3", source_file="README.md"),
        Command(name="cmd4", source_file="Makefile"),
        Command(name="cmd5", source_file="Makefile"),
        Command(name="cmd6", source_file="Makefile"),
        Command(name="orphan-cmd"),  # no source_file
    ]
    groups = _build_command_groups(cmds, [], [], 6, True)

    assert len(groups) == 3
    general = next(g for g in groups if g.slug == "general")
    assert len(general.commands) == 1
    assert general.commands[0].name == "orphan-cmd"
