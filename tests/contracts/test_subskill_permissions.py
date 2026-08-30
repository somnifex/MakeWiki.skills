"""Subskill permission contract.

Each ``subskills/*/SKILL.md`` front-matter declares the tools the subskill is
allowed to use. This contract guards specific permission requirements that the
execution flow depends on — most importantly that the Review subskill can
revise files in place (its Step 3 performs in-place revision of the target
docs), which requires ``Edit`` / ``Write``.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _frontmatter_tools(skill_md: Path) -> set[str]:
    """Return the tool names listed in the ``allowed-tools`` front-matter line.

    Parses only the YAML front-matter block delimited by ``---``; returns the
    individual tool words (``Read``, ``Write``, ``Edit``, ``Grep``, ...) with
    any ``Bash(...)`` qualifier collapsed to its bare ``Bash`` name.
    """
    text = skill_md.read_text(encoding="utf-8")
    match = _frontmatter_block(text)
    tools: set[str] = set()
    for line in match.splitlines():
        stripped = line.strip()
        if not stripped.startswith("allowed-tools"):
            continue
        value = stripped.split(":", 1)[1]
        for token in value.split():
            if token.startswith("Bash"):
                tools.add("Bash")
            elif token == "Read" or token == "Write" or token == "Edit":
                tools.add(token)
            elif token in {"Glob", "Grep"}:
                tools.add(token)
    return tools


def _frontmatter_block(text: str) -> str:
    """Return the front-matter block between the leading ``---`` fences."""
    if not text.startswith("---\n"):
        return ""
    end = text.find("\n---\n", 4)
    if end == -1:
        return ""
    return text[4:end]


def test_review_skill_has_edit_permission():
    """makewiki-review must be able to revise files in place.

    The Review subskill's Step 3 revises the target documentation in place, so
    its ``allowed-tools`` front-matter must include both ``Edit`` and ``Write``.
    """
    skill_md = PROJECT_ROOT / "subskills" / "review" / "SKILL.md"
    assert skill_md.is_file(), "subskills/review/SKILL.md is missing"
    tools = _frontmatter_tools(skill_md)
    assert "Edit" in tools, "subskills/review/SKILL.md allowed-tools must include Edit"
    assert "Write" in tools, "subskills/review/SKILL.md allowed-tools must include Write"


def test_review_skill_frontmatter_declares_allowed_tools():
    """makewiki-review must actually declare an allowed-tools line."""
    skill_md = PROJECT_ROOT / "subskills" / "review" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "allowed-tools" in _frontmatter_block(text), (
        "subskills/review/SKILL.md is missing the allowed-tools front-matter "
        "entry the permission contract depends on"
    )
