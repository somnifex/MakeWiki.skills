"""Subskill CLI flag contract.

Each ``subskills/*/SKILL.md`` documents flags the user is expected to pass
(e.g. ``--format json``, ``--target confluence|notion``, ``--wiki-dir <path>``).
This contract walks each subskill markdown, extracts the flag forms it lists,
and verifies that the corresponding Typer command actually accepts those flags.

It does **not** require an exact 1-to-1 match — additional CLI flags are
allowed — but every flag a subskill advertises must exist on the
corresponding Typer command.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import typer

from makewiki_skills.cli import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Map subskill name to the Typer command it documents as its primary surface.
SUBSKILL_TO_COMMAND: dict[str, str] = {
    "scan": "evidence",                # subskills/scan documents the `evidence` command
    "site": "build-site",
    "export": "export",
    "sync": "sync-bundle",
    "init": "init-config",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _iter_command_options(cmd_name: str) -> set[str]:
    """Return the set of CLI option names accepted by the Typer command."""
    target = next(
        (
            cmd
            for cmd in app.registered_commands
            if (cmd.name or (cmd.callback.__name__ if cmd.callback else "")) == cmd_name
        ),
        None,
    )
    if target is None:
        raise AssertionError(f"Typer command {cmd_name!r} is not registered")
    callback = target.callback
    if callback is None:
        return set()
    flags: set[str] = set()
    sig = inspect.signature(callback)
    for pname, param in sig.parameters.items():
        default = param.default
        param_decls = getattr(default, "param_decls", None) or getattr(default, "opts", None)
        if param_decls:
            for decl in param_decls:
                if isinstance(decl, str) and decl.startswith("--"):
                    flags.add(decl)
    return flags


def _documented_flags(subskill_md: Path) -> set[str]:
    """Extract ``--flag`` and ``--flag value`` mentions from the markdown."""
    text = _read(subskill_md)
    # Flags appear either as `--format`, `[--format ...]`, or in code fences.
    flag_pattern = re.compile(r"`?(--[a-z][a-z0-9-]+(?:[\s|\]<][^`]*)?)`?")
    flags: set[str] = set()
    for match in flag_pattern.finditer(text):
        token = match.group(1).split()[0]
        token = token.rstrip(",]")
        if token.startswith("--"):
            flags.add(token)
    return flags


def test_subskill_documented_flags_exist_on_cli():
    violations: list[str] = []
    for subskill_name, command_name in SUBSKILL_TO_COMMAND.items():
        skill_md = PROJECT_ROOT / "subskills" / subskill_name / "SKILL.md"
        if not skill_md.is_file():
            continue
        documented = _documented_flags(skill_md)
        actual = _iter_command_options(command_name)
        # Subtract "false positive" flags from surrounding prose that happen to
        # mention a CLI flag with no claim on the specific command.
        # Only enforce flags that look like real tool options (must be at
        # least one alphabetical char after the leading dashes).
        for flag in sorted(documented):
            if flag in actual:
                continue
            # Some flags (like --version / --help) are universal.
            if flag in {"--help", "--version", "-h"}:
                continue
            # Cross-tool flags documented for completeness: skip if the
            # command only differs in supported set.
            violations.append(
                f"{skill_md.relative_to(PROJECT_ROOT)} documents {flag} but {command_name!r} does not accept it"
            )
    assert not violations, "\n".join(violations)


def test_subskill_documents_execution_block():
    """Every subskill markdown shows how to invoke the underlying CLI."""
    for subskill_name in SUBSKILL_TO_COMMAND:
        skill_md = PROJECT_ROOT / "subskills" / subskill_name / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = _read(skill_md)
        if "run_toolkit.py" not in text:
            violations: list[str] = [f"{skill_md.relative_to(PROJECT_ROOT)} lacks run_toolkit.py invocation"]
            assert not violations, "\n".join(violations)


def test_unknown_subskill_command_mapping_fails_fast():
    """Sanity guard: every entry in SUBSKILL_TO_COMMAND resolves to a registered Typer cmd."""
    for subskill_name, command_name in SUBSKILL_TO_COMMAND.items():
        names = {
            cmd.name or (cmd.callback.__name__ if cmd.callback else "")
            for cmd in app.registered_commands
        }
        assert command_name in names, (
            f"subskill {subskill_name!r} maps to unknown Typer command {command_name!r}"
        )
