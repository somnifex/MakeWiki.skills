"""Tests for OutputValidator (mechanical L0 checks only)."""

from pathlib import Path

from makewiki_skills.renderer.validator import OutputValidator


def test_validator_accepts_structural_content(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "README.md").write_text(
        "# Demo\n\n## Quick Start\n\n```bash\ndemo run\n```\n",
        encoding="utf-8",
    )

    report = OutputValidator().validate(output_dir)

    assert report.files_checked == 1
    assert report.passed
    assert not any(issue.severity == "error" for issue in report.issues)


def test_validator_flags_empty_page(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "EMPTY.md").write_text("# Demo\n", encoding="utf-8")

    report = OutputValidator().validate(output_dir)

    assert any(issue.issue_type == "empty_page" for issue in report.issues)


def test_validator_flags_missing_dir(tmp_path: Path):
    output_dir = tmp_path / "does-not-exist"

    report = OutputValidator().validate(output_dir)

    assert any(issue.issue_type == "missing_dir" for issue in report.issues)
    assert any(issue.severity == "error" for issue in report.issues)


def test_validator_counts_files_with_issues(tmp_path: Path):
    output_dir = tmp_path / "makewiki"
    output_dir.mkdir()
    (output_dir / "EMPTY.md").write_text("# Demo\n", encoding="utf-8")
    (output_dir / "OK.md").write_text(
        "# Good\n\n## Quick Start\n\n```bash\ndemo\n```\n", encoding="utf-8"
    )

    report = OutputValidator().validate(output_dir)

    assert report.files_checked == 2
    assert report.files_with_issues == 1
