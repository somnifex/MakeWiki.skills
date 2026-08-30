"""CLI ↔ Skill documentation contract.

Every Typer command registered on ``makewiki_skills.cli:app`` must be
traceable in the documentation set (``AGENTS.md``, ``references/api.md``,
each ``subskills/*/SKILL.md``, and the root ``SKILL.md``). Likewise, every
command documented in those files must resolve to a registered Typer
command.

Two leniency classes exist:

* ``legacy-generate`` and its ``generate`` alias form the non-authoritative,
  deterministic-scaffold family. They are ``NOT`` the authoritative ``/makewiki``
  LLM path, and are never advertised in prose as such. Because the docs are not
  required to name the mechanical fallback, their presence is not demanded;
  what IS enforced is that they are never presented as authoritative.
* Other deprecation aliases (``scan``, ``verify``, ``sync``) are listed
  explicitly in the Aliases table and must be documented in ``references/api.md``.

``review`` is a standalone command (it runs ``CrossLanguageReviewer`` over
existing output); it is NOT an alias of ``parity``.
"""

from __future__ import annotations

import re
from pathlib import Path

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
    "generate": "legacy-generate",
    "scan": "evidence",
    "verify": "verify-docs",
    "sync": "sync-bundle",
}

# The non-authoritative, deterministic-scaffold family. ``legacy-generate`` is
# the canonical (but mechanical-only) command; ``generate`` is its deprecated
# alias. Neither is the authoritative ``/makewiki`` LLM path. They are exempt
# from the "must be named in prose docs" presence check — the docs are not
# required to advertise the mechanical fallback — but they must NEVER be
# documented as authoritative (guarded by
# ``test_legacy_family_never_presented_as_authoritative``).
NON_AUTHORITATIVE_COMMANDS: set[str] = {"legacy-generate", "generate"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _all_documentation_files() -> list[Path]:
    """Every documentation file that may reference CLI commands.

    Covers the root docs (SKILL, AGENTS, CLAUDE, README in both languages), all
    subskill SKILL.md files, every reference doc, any ``tasks/**`` planning
    docs, and the launcher scripts that actually invoke the CLI. A command the
    docs tell the user to run should resolve to a registered Typer command.
    """
    files: list[Path] = [
        PROJECT_ROOT / "SKILL.md",
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "CLAUDE.md",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "README.en.md",
    ]
    for sub in sorted((PROJECT_ROOT / "subskills").glob("*/SKILL.md")):
        files.append(sub)
    for ref in sorted((PROJECT_ROOT / "references").glob("*.md")):
        files.append(ref)
    for task in sorted((PROJECT_ROOT / "tasks").glob("**/*.md")):
        files.append(task)
    for script in sorted((PROJECT_ROOT / "scripts").glob("*.py")):
        files.append(script)
    return files


# Words that the broad backtick scan picks up from code-fence blocks and table
# cells but that are NOT CLI command names — prose nouns, CLI argument values,
# and documentation vocabulary. Keeping them here lets the "every documented
# command is registered" test run over the full doc corpus without drowning in
# non-command tokens, while any genuinely documented-but-unregistered command
# name still fails. This is intentionally NOT the tautological "only look at
# tokens we already know are registered" filter.
NON_COMMAND_TOKENS: frozenset[str] = frozenset(
    {
        "adjudicated",
        "all",
        "auto",
        "claim",
        "commands",
        "configuration",
        "description",
        "faq",
        "identity",
        "installation",
        "name",
        "pdf",
        "perspective",
        "provenance",
        "troubleshooting",
        "version",
    }
)


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
    """Every registered Typer command is referenced in at least one doc.

    The non-authoritative legacy scaffold family (``legacy-generate`` /
    ``generate``) is exempt from the literal-presence requirement — those
    commands are guarded instead by
    ``test_legacy_family_never_presented_as_authoritative``, which asserts they
    are never promoted as the authoritative path.
    """
    missing: list[str] = []
    for cmd in sorted(REGISTERED_COMMANDS):
        if cmd in NON_AUTHORITATIVE_COMMANDS:
            continue
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
    """Every backtick-wrapped CLI command mentioned in the docs is registered.

    This is the real (non-tautological) direction of the contract: we extract
    every backtick token that looks like a command name from code-fence blocks
    and table cells across the FULL documentation corpus, then assert that each
    — excluding a small curated list of prose/vocabulary tokens — resolves to a
    registered Typer command. A command the docs tell the user to run but that
    was never wired up into the CLI now fails loudly.

    The previous version pre-filtered ``cli_candidates`` through
    ``REGISTERED_COMMANDS`` before asserting, which made the test pass
    trivially (the difference of a set and a superset of it is always empty).
    """
    pattern = re.compile(r"`([a-z][a-z0-9-]*)`")
    referenced: set[str] = set()
    for doc in _all_documentation_files():
        text = _read(doc)
        for block in _code_fence_blocks(text):
            for match in pattern.finditer(block):
                referenced.add(match.group(1))
        for row in _table_rows(text):
            for cell in row:
                for match in pattern.finditer(cell):
                    referenced.add(match.group(1))
    # The candidate set is NOT pre-filtered through REGISTERED_COMMANDS (that
    # would make this test tautological). We only subtract a curated list of
    # prose/vocabulary tokens; any remaining token must be a registered command.
    documented = {name for name in referenced if name not in NON_COMMAND_TOKENS}
    extras = documented - REGISTERED_COMMANDS
    assert not extras, (
        "Docs reference CLI commands that are not registered: "
        + ", ".join(sorted(extras))
    )


def test_legacy_family_never_presented_as_authoritative():
    """Neither `legacy-generate` nor its `generate` alias may be presented as
    the authoritative command.

    The deterministic scaffold is the non-authoritative, mechanical-only
    regression path. The authoritative flow is the LLM-driven `/makewiki`.
    This guards against the split-brain that Phase-2 deleted: a "generate"
    path that quietly ran the deterministic scaffold instead of the
    LLM-orchestrated flow.
    """
    for cmd in sorted(NON_AUTHORITATIVE_COMMANDS):
        forbidden_patterns = [
            re.compile(r"`" + re.escape(cmd) + r"`\s+is\s+the\s+authoritative", re.IGNORECASE),
            re.compile(r"run\s+`" + re.escape(cmd) + r"`", re.IGNORECASE),
            re.compile(r"`" + re.escape(cmd) + r"`\s+command\s+is\s+authoritative", re.IGNORECASE),
            re.compile(r"`" + re.escape(cmd) + r"`\s+as\s+the\s+authoritative", re.IGNORECASE),
        ]
        violations: list[str] = []
        for doc in _all_documentation_files():
            text = _read(doc)
            for pattern in forbidden_patterns:
                if pattern.search(text):
                    violations.append(f"{doc.relative_to(PROJECT_ROOT)}: {pattern.pattern}")
        assert not violations, (
            f"`{cmd}` must never be presented as authoritative:\n" + "\n".join(violations)
        )


def test_deprecated_aliases_are_listed_in_api_md():
    """references/api.md explicitly lists each deprecation alias.

    ``generate``'s target (``legacy-generate``) is part of the non-authoritative
    legacy family — the docs are not required to name the mechanical fallback,
    so its target check is waived (its non-authoritative framing is instead
    enforced by ``test_legacy_family_never_presented_as_authoritative``).
    """
    text = _read(PROJECT_ROOT / "references" / "api.md")
    for alias, target in DEPRECATED_ALIASES.items():
        assert f"`{alias}`" in text, f"references/api.md must document `{alias}`"
        if target in NON_AUTHORITATIVE_COMMANDS:
            continue
        assert f"`{target}`" in text, f"references/api.md must reference `{target}`"
