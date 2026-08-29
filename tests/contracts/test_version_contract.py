"""Version Contract: every version source across the repo agrees.

The skill↔toolkit version is bound together (see CLAUDE.md "Version binding").
This contract asserts that each canonical version source reports the same
value, so a version bump cannot silently land in one place and not the others.

Sources checked:
- ``pyproject.toml``       (``project.version``)
- ``src/makewiki_skills/__init__.py`` (``__version__``)
- ``.claude-plugin/plugin.json`` (``version``)
- root ``SKILL.md`` front-matter (``version``)
- ``scripts/bootstrap_toolkit.py`` (``DEFAULT_VERSION``)
- every ``subskills/*/SKILL.md`` front-matter (``version``)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SUBSKILLS = (
    "export",
    "init",
    "review",
    "scan",
    "site",
    "sync",
    "validate",
)


def _front_matter_version(text: str) -> str:
    """Extract the ``version:`` line value from a SKILL.md ``---`` front-matter block."""
    match = re.search(r"^version:\s*['\"]?([^'\"\n]+)['\"]?", text, re.MULTILINE)
    assert match, "front-matter has no version: field"
    return match.group(1).strip()


def _assert_version_equal(canonical: str, label: str, actual: str) -> None:
    assert actual == canonical, (
        f"version drift in {label}: expected {canonical}, found {actual}"
    )


@pytest.fixture(scope="module")
def canonical_version() -> str:
    """The reference version, taken from pyproject.toml."""
    text = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    assert match, "pyproject.toml has no project.version"
    return match.group(1)


def test_pyproject_version(canonical_version: str) -> None:
    _assert_version_equal(canonical_version, "pyproject.toml", canonical_version)


def test_package___version__(canonical_version: str) -> None:
    text = (PROJECT_ROOT / "src" / "makewiki_skills" / "__init__.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r"^__version__\s*=\s*['\"]([^'\"]+)['\"]", text, re.MULTILINE)
    assert match, "__init__.py has no __version__"
    _assert_version_equal(canonical_version, "src/makewiki_skills/__init__.py", match.group(1))


def test_plugin_json_version(canonical_version: str) -> None:
    text = (PROJECT_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    match = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    assert match, "plugin.json has no version"
    _assert_version_equal(canonical_version, ".claude-plugin/plugin.json", match.group(1))


def test_root_skill_version(canonical_version: str) -> None:
    text = (PROJECT_ROOT / "SKILL.md").read_text(encoding="utf-8")
    _assert_version_equal(
        canonical_version, "SKILL.md front-matter", _front_matter_version(text)
    )


def test_bootstrap_default_version(canonical_version: str) -> None:
    text = (PROJECT_ROOT / "scripts" / "bootstrap_toolkit.py").read_text(encoding="utf-8")
    match = re.search(r'^DEFAULT_VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    assert match, "bootstrap_toolkit.py has no DEFAULT_VERSION"
    _assert_version_equal(
        canonical_version, "scripts/bootstrap_toolkit.py DEFAULT_VERSION", match.group(1)
    )


@pytest.mark.parametrize("subskill", SUBSKILLS)
def test_subskill_skill_versions(canonical_version: str, subskill: str) -> None:
    """Every subskills/*/SKILL.md reports the same version as the root."""
    path = PROJECT_ROOT / "subskills" / subskill / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    _assert_version_equal(
        canonical_version,
        f"subskills/{subskill}/SKILL.md front-matter",
        _front_matter_version(text),
    )
