"""Regression tests for the repo-local launcher instructions in skill docs."""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
MAKEWIKI_SKILL_DIRS = [
    "makewiki",
    "makewiki-scan",
    "makewiki-review",
    "makewiki-validate",
    "makewiki-init",
]


def test_makewiki_skills_use_repo_local_launcher():
    for skill_dir in MAKEWIKI_SKILL_DIRS:
        text = (SKILLS_DIR / skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "scripts/run_toolkit.py" in text
        assert ".venv" in text
        assert "`uv`" in text
        assert "`python -m venv`" in text


def test_makewiki_skills_do_not_depend_on_claude_skill_dir_env_var():
    for skill_dir in MAKEWIKI_SKILL_DIRS:
        text = (SKILLS_DIR / skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "CLAUDE_SKILL_DIR" not in text


def test_makewiki_skills_do_not_call_global_toolkit_directly():
    for skill_dir in MAKEWIKI_SKILL_DIRS:
        text = (SKILLS_DIR / skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "python -m makewiki_skills" not in text
