"""Checks for the MakeWiki orchestrator skill contract."""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"


def test_makewiki_skill_contains_hard_rules() -> None:
    text = (SKILLS_DIR / "makewiki" / "SKILL.md").read_text(encoding="utf-8")

    assert "Do not summarize or quote the content of module briefs / traces in the main conversation." in text
    assert "Only read child-skill receipts that contain status, artifact_path, trace_path, error_code, and attempt." in text


def test_internal_child_skills_exist() -> None:
    expected = [
        "makewiki-llm-scan",
        "makewiki-surface-card",
        "makewiki-semantic-root",
        "makewiki-module-brief",
        "makewiki-workflow-brief",
        "makewiki-page-plan",
        "makewiki-page-write",
        "makewiki-page-repair",
    ]
    for name in expected:
        assert (SKILLS_DIR / name / "SKILL.md").is_file(), f"Missing {name}/SKILL.md"


def test_legacy_render_stack_is_removed() -> None:
    repo_root = SKILLS_DIR.parent
    removed_paths = [
        repo_root / "src" / "makewiki_skills" / "generator" / "language_generator.py",
        repo_root / "src" / "makewiki_skills" / "model" / "semantic_model.py",
        repo_root / "src" / "makewiki_skills" / "model" / "task_inference.py",
        repo_root / "src" / "makewiki_skills" / "templates" / "base" / "usage" / "basic-usage.md.j2",
    ]
    for path in removed_paths:
        assert not path.exists(), f"Legacy artifact still exists: {path}"
