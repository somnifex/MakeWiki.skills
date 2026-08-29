"""Regression tests for shell-safe skill command snippets."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CODE_FENCE_RE = re.compile(r"```(?P<lang>[^\n]*)\n(?P<body>.*?)```", re.DOTALL)
COMMAND_FENCE_LANGS = {"!", "bash", "sh", "shell"}
BANNED_PATTERNS = {
    "auto-executing ```! fence": re.compile(r"^!$"),
    "shell short-circuit (||)": re.compile(r"\|\|"),
    "shell chaining (&&)": re.compile(r"&&"),
    "stderr redirection to /dev/null": re.compile(r"\d?>/dev/null"),
    "bash-style parameter expansion": re.compile(r"\$\{[^}]+\}"),
    "raw $ARGUMENTS placeholder in a runnable command": re.compile(r"\$ARGUMENTS\b"),
}


def _scan_targets() -> list[Path]:
    """All skill markdown files whose fenced commands must stay shell-safe."""
    targets: list[Path] = []
    targets.extend(PROJECT_ROOT.glob("SKILL.md"))
    targets.extend(PROJECT_ROOT.glob("subskills/**/SKILL.md"))
    targets.extend(PROJECT_ROOT.glob("tasks/**/*.md"))
    targets.extend(PROJECT_ROOT.glob("references/**/*.md"))
    # Sub-skill examples & scripts docs are also user-facing.
    targets.extend(PROJECT_ROOT.glob("subskills/*/examples/**/*.md"))
    targets.extend(PROJECT_ROOT.glob("subskills/*/references/**/*.md"))
    targets.extend(PROJECT_ROOT.glob("subskills/*/scripts/**/*.md"))
    return sorted(set(targets))


def iter_command_fences():
    for skill_file in _scan_targets():
        text = skill_file.read_text(encoding="utf-8")
        for match in CODE_FENCE_RE.finditer(text):
            lang = match.group("lang").strip()
            body = match.group("body").strip()
            if lang in COMMAND_FENCE_LANGS:
                yield skill_file, lang, body


def test_skill_command_fences_avoid_shell_only_patterns():
    violations: list[str] = []

    for skill_file, lang, body in iter_command_fences():
        for description, pattern in BANNED_PATTERNS.items():
            if pattern.search(lang) or pattern.search(body):
                first_line = body.splitlines()[0] if body else "<empty>"
                violations.append(
                    f"{skill_file.relative_to(PROJECT_ROOT)} uses {description}: {first_line}"
                )

    assert not violations, "Unsafe skill command snippets found:\n" + "\n".join(violations)


def test_no_raw_dollar_arguments_in_skill_bodies():
    """$ARGUMENTS must never appear as a literal token in a runnable fence.

    The Skill layer expands $ARGUMENTS at the host level; the fenced body is
    what an agent will copy/paste into Bash, so a literal $ARGUMENTS there
    would silently drop the user's arguments on most shells.
    """
    pattern = re.compile(r"\$ARGUMENTS\b")
    violations: list[str] = []
    for skill_file, lang, body in iter_command_fences():
        if pattern.search(body):
            first_line = body.splitlines()[0] if body else "<empty>"
            violations.append(
                f"{skill_file.relative_to(PROJECT_ROOT)} contains literal $ARGUMENTS in {lang!r} fence: {first_line}"
            )
    assert not violations, "Literal $ARGUMENTS in runnable fence:\n" + "\n".join(violations)


def test_scan_targets_exist_for_phase_8_expansion():
    """Guard against accidental glob regression: the scan set must be non-empty
    and include ``tasks/`` + ``references/`` to satisfy Phase-8.
    """
    targets = _scan_targets()
    assert targets, "scan set is empty — shell-safety coverage regressed"
    kinds = {p.relative_to(PROJECT_ROOT).parts[0] for p in targets}
    assert "tasks" in kinds, "scan set must include tasks/*.md (Phase-8 expansion)"
    assert "references" in kinds, "scan set must include references/*.md (Phase-8 expansion)"
