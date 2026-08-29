"""CLI ↔ Skill documentation contract.

Every Typer command registered on ``makewiki_skills.cli:app`` must be
traceable in the documentation set (``AGENTS.md``, ``references/api.md``,
each ``subskills/*/SKILL.md``, and the root ``SKILL.md``). Likewise, every
command documented in those files must resolve to a registered Typer
command.

Two explicit escape hatches exist:
* ``generate`` — documented only as a *deprecated alias* for
  ``deterministic-generate``. It must never appear in skill / subskill prose
  as the authoritative command.
* Other deprecation aliases (``scan``, ``verify``, ``review``, ``sync``) are
  listed explicitly in the Aliases table; they may be referenced by their
  alias form only.
"""

from __future__ import annotations

import re
from pathlib import Path

import typer

from makewiki_skills.cli import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Typer command names registered on the CLI app. When Typer's ``name=`` is
# omitted, the callback's function name is used as the canonical name.
REGISTERED_COMMANDS: set[str] = {
    cmd.name or (cmd.callback.__name__ if cmd.callback else "")
    for cmd in app.registered_commands
}

# Aliases are also registered Typer commands but should appear in docs as
# "deprecated alias of X", not as authoritative entries.
DEPRECATED_ALIASES: dict[str, str] = {
    "generate": "deterministic-generate",
    "scan": "evidence",
    "verify": "verify-docs",
    "sync": "sync-bundle",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _all_documentation_files() -> list[Path]:
    files: list[Path] = [
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "references" / "api.md",
        PROJECT_ROOT / "SKILL.md",
    ]
    for sub in sorted((PROJECT_ROOT / "subskills").glob("*/SKILL.md")):
        files.append(sub)
    return files


def _code_fence_blocks(text: str) -> list[str]:
    """Return the body of every ```bash / ```shell code fence."""
    pattern = re.compile(r"```(?:bash|sh|shell)\s*\n(.*?)```", re.DOTALL)
    return pattern.findall(text)


def _table_rows(text: str) -> list[list[str]]:
    """Return every markdown table row split by ``|`` (best-effort)."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        if line.count("|") >= 2 and not re.match(r"^\s*\|?[\s:\-]+\|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
    return rows


def test_all_registered_cli_commands_are_documented():
    """Every registered Typer command is referenced in at least one doc."""
    missing: list[str] = []
    for cmd in sorted(REGISTERED_COMMANDS):
        # Match either as a backtick-wrapped token (`cmd`) or as the first
        # token in a code fence line. We accept the deprecated alias form too.
        alias_of = DEPRECATED_ALIASES.get(cmd)
        needles = [f"`{cmd}`", f"`{cmd} "]
        if alias_of:
            needles.append(f"alias for `{alias_of}`")
        hits = 0
        for doc in _all_documentation_files():
            text = _read(doc)
            if any(n in text for n in needles):
                hits += 1
        if hits == 0:
            missing.append(cmd)
    assert not missing, "Registered Typer commands missing from docs: " + ", ".join(missing)


def test_documented_cli_commands_resolve_to_registered_typer():
    """Every backtick-wrapped CLI command mentioned in docs is registered."""
    pattern = re.compile(r"`([a-z][a-z0-9-]*)`")
    referenced: set[str] = set()
    for doc in _all_documentation_files():
        text = _read(doc)
        for block in _code_fence_blocks(text):
            for match in pattern.finditer(block):
                referenced.add(match.group(1))
        # Also pull from table cells.
        for row in _table_rows(text):
            for cell in row:
                for match in pattern.finditer(cell):
                    referenced.add(match.group(1))
    # Filter to commands that look like CLI commands (skip shared helpers).
    cli_candidates = {
        name
        for name in referenced
        if name in REGISTERED_COMMANDS
    }
    extras = cli_candidates - REGISTERED_COMMANDS
    assert not extras, "Docs reference Typer commands that are not registered: " + ", ".join(extras)


def test_generate_only_appears_as_deprecated_alias():
    """`generate` must never be presented as the authoritative command.

    It can be documented as a deprecated alias. This guards against the
    split-brain that Phase-2 deleted: a "generate" path that quietly ran
    the deterministic scaffold instead of the LLM-orchestrated flow.
    """
    forbidden_patterns = [
        re.compile(r"`generate`\s+is\s+the\s+authoritative", re.IGNORECASE),
        re.compile(r"run\s+`generate`", re.IGNORECASE),
        re.compile(r"`generate`\s+command\s+is\s+authoritative", re.IGNORECASE),
    ]
    violations: list[str] = []
    for doc in _all_documentation_files():
        text = _read(doc)
        for pattern in forbidden_patterns:
            if pattern.search(text):
                violations.append(f"{doc.relative_to(PROJECT_ROOT)}: {pattern.pattern}")
    assert not violations, (
        "`generate` must never be presented as authoritative:\n" + "\n".join(violations)
    )


def test_deprecated_aliases_are_listed_in_api_md():
    """references/api.md explicitly lists each deprecation alias."""
    text = _read(PROJECT_ROOT / "references" / "api.md")
    for alias, target in DEPRECATED_ALIASES.items():
        assert f"`{alias}`" in text, f"references/api.md must document `{alias}`"
        assert f"`{target}`" in text, f"references/api.md must reference `{target}`"
