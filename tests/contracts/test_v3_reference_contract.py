"""Documentation reference contract: V3 references resolve and are classified.

Purely deterministic assertions over the reference layer:

* every ``.md`` file the v3 README lists actually exists;
* every explicit ``references/v3/*.md`` path in the active docs
  (SKILL.md, AGENTS.md, CLAUDE.md, tasks/, subskills/, references/)
  resolves to a real file;
* ``PHASE_PROMPTS.md`` is not an active reference (historical prose in the
  migration record is tolerated, a listed entry is not);
* the runtime authority set does NOT declare the contributor/historical
  documents (MIGRATION_PLAN, BASELINE, config-migration,
  LOCAL_AGENT_RULES) as runtime authority.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
V3 = PROJECT_ROOT / "references" / "v3"

RUNTIME_AUTHORITY = {
    "ARCHITECTURE.md",
    "COGNITIVE_BOUNDARY.md",
    "MULTI_AGENT_PROTOCOL.md",
    "SUBTASK_PROTOCOL.md",
    "ARTIFACT_CONTRACTS.md",
    "DOCUMENTATION_MODEL.md",
    "API_REFERENCE.md",
    "PAGE_SPEC.md",
    "QUALITY_POLICY.md",
}

HISTORICAL = {
    "BASELINE.md",
    "MIGRATION_PLAN.md",
    "config-migration.md",
    "LOCAL_AGENT_RULES.md",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def test_every_runtime_authority_file_exists():
    missing = [name for name in sorted(RUNTIME_AUTHORITY) if not (V3 / name).is_file()]
    assert not missing, f"runtime authority files missing on disk: {missing}"


def test_every_historical_file_exists():
    missing = [name for name in sorted(HISTORICAL) if not (V3 / name).is_file()]
    assert not missing, f"historical files missing on disk: {missing}"


def test_readme_lists_runtime_authority_and_historical_sections():
    text = _read(V3 / "README.md")
    for name in sorted(RUNTIME_AUTHORITY):
        assert f"`{name}`" in text, f"v3 README must list runtime authority {name}"
    for name in sorted(HISTORICAL):
        assert f"`{name}`" in text, f"v3 README must list historical doc {name}"
    # The two sections must be distinguishable.
    assert "Runtime authority" in text
    assert "historical" in text.lower()
    # Historical files must not appear in the runtime authority section.
    runtime_section = text.split("Runtime authority", 1)[1].split("##", 1)[0]
    for name in sorted(HISTORICAL):
        assert name not in runtime_section, (
            f"{name} must not be listed under the runtime authority section"
        )


def test_phase_prompts_is_not_an_active_reference():
    """PHASE_PROMPTS.md was removed after migration; no active reference may
    list it as an existing resource (a historical note explaining its removal
    is acceptable). The file itself must not exist."""
    assert not (V3 / "PHASE_PROMPTS.md").is_file()
    readme = _read(V3 / "README.md")
    assert "PHASE_PROMPTS.md" not in readme, (
        "v3 README must not reference the removed PHASE_PROMPTS.md"
    )
    # Active runtime authority docs must not point at it either.
    for name in sorted(RUNTIME_AUTHORITY):
        assert "PHASE_PROMPTS" not in _read(V3 / name), (
            f"runtime reference {name} must not reference PHASE_PROMPTS"
        )


def test_explicit_v3_paths_in_active_docs_resolve():
    """Every explicit ``references/v3/<name>.md`` path in the active doc set
    resolves to an existing file."""
    docs: list[Path] = [PROJECT_ROOT / "SKILL.md", PROJECT_ROOT / "AGENTS.md", PROJECT_ROOT / "CLAUDE.md"]
    docs += sorted((PROJECT_ROOT / "tasks").glob("**/*.md"))
    docs += sorted((PROJECT_ROOT / "subskills").glob("*/SKILL.md"))
    docs += sorted((PROJECT_ROOT / "references").glob("*.md"))
    pattern = re.compile(r"references/v3/([A-Za-z0-9_.\-]+\.md)")
    broken: list[str] = []
    for doc in docs:
        for match in pattern.finditer(_read(doc)):
            name = match.group(1)
            if not (V3 / name).is_file():
                broken.append(f"{doc.relative_to(PROJECT_ROOT)} -> {name}")
    assert not broken, f"broken references/v3 links: {broken}"


def test_historical_docs_are_not_runtime_pointers_from_skill():
    """SKILL.md must not direct the runtime agent to read the
    contributor/historical documents as part of progressive disclosure."""
    skill = _read(PROJECT_ROOT / "SKILL.md")
    for name in sorted(HISTORICAL):
        assert name not in skill, (
            f"SKILL.md must not point the runtime agent at historical doc {name}"
        )


def test_historical_docs_carry_not_runtime_authority_banner():
    for name in sorted(HISTORICAL):
        text = _read(V3 / name)
        assert "NOT runtime authority" in text, (
            f"{name} must carry the 'NOT runtime authority' banner"
        )
