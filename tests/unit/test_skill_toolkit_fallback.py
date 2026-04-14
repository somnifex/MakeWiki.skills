"""Regression tests for the home-scoped toolkit instructions in skill docs."""

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


def test_makewiki_skills_use_home_toolkit_bootstrap():
    for skill_dir in MAKEWIKI_SKILL_DIRS:
        skill_root = SKILLS_DIR / skill_dir
        text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        assert (skill_root / "scripts" / "bootstrap_toolkit.py").is_file()
        assert "scripts/bootstrap_toolkit.py" in text
        assert "scripts/run_toolkit.py" in text
        assert ".makewiki" in text
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


def test_makewiki_skill_bootstrap_scripts_are_identical():
    baseline = (SKILLS_DIR / MAKEWIKI_SKILL_DIRS[0] / "scripts" / "bootstrap_toolkit.py").read_text(
        encoding="utf-8"
    )
    for skill_dir in MAKEWIKI_SKILL_DIRS[1:]:
        text = (SKILLS_DIR / skill_dir / "scripts" / "bootstrap_toolkit.py").read_text(
            encoding="utf-8"
        )
        assert text == baseline
