"""Regression tests for shell-safe skill command snippets."""

from __future__ import annotations

import re
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
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


def iter_command_fences():
    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
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
                    f"{skill_file.relative_to(SKILLS_DIR.parent)} uses {description}: {first_line}"
                )

    assert not violations, "Unsafe skill command snippets found:\n" + "\n".join(violations)
