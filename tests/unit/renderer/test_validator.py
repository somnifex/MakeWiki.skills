"""Tests for OutputValidator."""

from pathlib import Path

from makewiki_skills.renderer.validator import OutputValidator


def test_validator_flags_banned_descriptor(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "README.md").write_text(
        "# Demo\n\nA powerful tool for users.\n",
        encoding="utf-8",
    )

    report = OutputValidator().validate(output_dir)

    assert any(issue.issue_type == "banned_descriptor" for issue in report.issues)


def test_validator_flags_developer_heading(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "README.md").write_text(
        "# Demo\n\n## Architecture\n\nInternal notes.\n",
        encoding="utf-8",
    )

    report = OutputValidator().validate(output_dir)

    assert any(issue.issue_type == "forbidden_heading" for issue in report.issues)


def test_validator_accepts_user_facing_page(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "README.md").write_text(
        "# Demo\n\n## Quick Start\n\n```bash\ndemo run\n```\n",
        encoding="utf-8",
    )

    report = OutputValidator().validate(output_dir)

    assert not any(issue.issue_type in {"banned_descriptor", "forbidden_heading"} for issue in report.issues)


def test_validator_accepts_module_heading(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    modules_dir = output_dir / "modules"
    modules_dir.mkdir(parents=True)
    (modules_dir / "core.md").write_text(
        "# Core Tasks\n\n## Module Overview\n\nRun the core workflow.\n",
        encoding="utf-8",
    )

    report = OutputValidator().validate(output_dir)

    assert not any(issue.issue_type == "forbidden_heading" for issue in report.issues)
