"""Bootstrap Reproducibility Contract.

The root ``scripts/bootstrap_toolkit.py`` is the canonical version-pinned +
integrity-checked bootstrap. It resolves an exact release tag
(``archive/refs/tags/v2.0.0.zip`` / ``--branch v2.0.0``) and records split,
distinct provenance: ``MAKEWIKI_TOOLKIT_VERSION`` (version),
``MAKEWIKI_TOOLKIT_COMMIT`` (Git identity for a Git install), and
``MAKEWIKI_TOOLKIT_ARCHIVE_SHA256`` (archive integrity checksum for an Archive
install). The legacy combined ``MAKEWIKI_TOOLKIT_SHA256`` is a warning-only
deprecated alias, not the contract. Every subskill ships a copy of this script
so each phase self-bootstraps identically.

The contract guards against supply-chain drift: it forbids any subskill copy
from silently reverting to the old behaviour of pulling an unpinned
``archive/refs/heads/main`` archive or an unversioned ``git clone`` of
``main`` (no checksum, moving target).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SUBSKILLS = (
    "export",
    "init",
    "review",
    "scan",
    "site",
    "sync",
    "validate",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_BOOTSTRAP = PROJECT_ROOT / "scripts" / "bootstrap_toolkit.py"


def _subskill_bootstraps() -> list[Path]:
    return [
        PROJECT_ROOT / "subskills" / name / "scripts" / "bootstrap_toolkit.py"
        for name in SUBSKILLS
    ]


def test_every_subskill_bootstrap_byte_identical_to_root():
    """Each subskills/*/scripts/bootstrap_toolkit.py must equal the canonical root script."""
    root_bytes = ROOT_BOOTSTRAP.read_bytes()
    differing = [
        str(path.relative_to(PROJECT_ROOT))
        for path in _subskill_bootstraps()
        if path.read_bytes() != root_bytes
    ]
    assert not differing, (
        "Subskill bootstrap copies drifted from the canonical root script: "
        + ", ".join(differing)
    )


def test_no_subskill_bootstrap_pulls_unpinned_main():
    """No subskill copy may reference refs/heads/main or an unversioned git clone."""
    offenders: list[str] = []
    for path in _subskill_bootstraps():
        text = path.read_text(encoding="utf-8")
        issues = []
        if "refs/heads/main" in text:
            issues.append("refs/heads/main")
        if "archive/refs/heads/" in text:
            issues.append("archive/refs/heads/")
        # An unversioned clone: `git clone` that is NOT pinned with --branch.
        if "git clone" in text and "--branch" not in text:
            issues.append("unversioned git clone (no --branch)")
        if issues:
            offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {', '.join(issues)}")
    assert not offenders, "Unpinned bootstrap found: " + "; ".join(offenders)


def test_root_bootstrap_carries_version_commit_and_archive_sha256():
    """The canonical root script must pin the version and support the split
    provenance contract: Git install binds version + commit, Archive install
    binds version + archive SHA256.

    The env names are distinct and non-overlapping:
    ``MAKEWIKI_TOOLKIT_VERSION`` (every install), ``MAKEWIKI_TOOLKIT_COMMIT``
    (Git identity), ``MAKEWIKI_TOOLKIT_ARCHIVE_SHA256`` (archive integrity
    checksum). The deprecated combined name ``MAKEWIKI_TOOLKIT_SHA256`` is kept
    as a warning-only alias but must NOT be the contract.
    """
    text = ROOT_BOOTSTRAP.read_text(encoding="utf-8")
    assert "MAKEWIKI_TOOLKIT_VERSION" in text, (
        "root bootstrap must resolve version from MAKEWIKI_TOOLKIT_VERSION"
    )
    # Git install: version + commit identity.
    assert "MAKEWIKI_TOOLKIT_COMMIT" in text, (
        "root bootstrap must support MAKEWIKI_TOOLKIT_COMMIT (Git install identity)"
    )
    # Archive install: version + archive SHA256 integrity checksum.
    assert "MAKEWIKI_TOOLKIT_ARCHIVE_SHA256" in text, (
        "root bootstrap must support MAKEWIKI_TOOLKIT_ARCHIVE_SHA256 (archive "
        "integrity checksum)"
    )
    assert "MAKEWIKI_TOOLKIT_COMMIT" != "MAKEWIKI_TOOLKIT_ARCHIVE_SHA256", (
        "commit identity and archive checksum must remain distinct env vars"
    )
    assert "refs/heads/main" not in text, (
        "root bootstrap must never pull the moving main branch"
    )



# ---------- Version-binding (requested == installed reuse, != replace) -------


def _load_bootstrap_module():
    """Load ``scripts/bootstrap_toolkit.py`` as an importable module."""
    spec = importlib.util.spec_from_file_location(
        "bootstrap_toolkit",
        PROJECT_ROOT / "scripts" / "bootstrap_toolkit.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_toolkit_root(tmp_path: Path, version: str) -> Path:
    """Build a minimal fake toolkit install root with a recorded VERSION marker."""
    root = tmp_path / "fake-toolkit"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "scripts").mkdir()
    (root / "scripts" / "run_toolkit.py").write_text("", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "makewiki_skills").mkdir(parents=True)
    (root / "src" / "makewiki_skills" / "__init__.py").write_text("", encoding="utf-8")
    (root / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    return root


def test_bootstrap_rejects_wrong_installed_version(tmp_path: Path, monkeypatch):
    """A stale installed version must be flagged for replacement."""
    bootstrap = _load_bootstrap_module()
    monkeypatch.setenv("MAKEWIKI_TOOLKIT_VERSION", "2.0.0")
    root = _fake_toolkit_root(tmp_path, version="1.0.0")

    assert bootstrap.installed_version(root) == "1.0.0"
    assert bootstrap.installed_version(root) != bootstrap.requested_version()
    assert bootstrap.needs_replacement(root, bootstrap.requested_version()) is True


def test_bootstrap_reuses_matching_version(tmp_path: Path, monkeypatch):
    """An install whose recorded version matches requested is reused."""
    bootstrap = _load_bootstrap_module()
    monkeypatch.setenv("MAKEWIKI_TOOLKIT_VERSION", "2.0.0")
    root = _fake_toolkit_root(tmp_path, version="2.0.0")

    assert bootstrap.installed_version(root) == bootstrap.requested_version()
    assert bootstrap.needs_replacement(root, bootstrap.requested_version()) is False


def test_bootstrap_persists_version_and_commit(tmp_path: Path):
    """record_version / record_commit write their distinct marker files."""
    bootstrap = _load_bootstrap_module()
    root = tmp_path / "toolkit"

    bootstrap.record_version(root, "2.0.0")
    bootstrap.record_commit(root, "a1b2c3d4")
    bootstrap.record_archive_sha256(root, "0" * 64)

    assert bootstrap.installed_version(root) == "2.0.0"
    assert (root / "VERSION").read_text(encoding="utf-8").strip() == "2.0.0"
    assert (root / ".toolkit-commit").read_text(encoding="utf-8").strip() == "a1b2c3d4"
    assert (
        root / ".toolkit-archive-sha256"
    ).read_text(encoding="utf-8").strip() == "0" * 64


def test_bootstrap_needs_replacement_requires_existing_install(tmp_path: Path):
    """An absent (or non-toolkit) root always needs replacement."""
    bootstrap = _load_bootstrap_module()
    empty = tmp_path / "empty"
    empty.mkdir()

    assert bootstrap.installed_version(empty) is None
    assert bootstrap.needs_replacement(empty, "2.0.0") is True


def test_bootstrap_marker_files_are_ignored_on_copy():
    """Marker files must never be copied from a source into an install."""
    bootstrap = _load_bootstrap_module()
    # shutil.ignore_patterns returns a callable — invoke it to see the exclusion set.
    ignored = bootstrap.IGNORE(bootstrap.toolkit_root(), ["VERSION", ".toolkit-commit", ".toolkit-archive-sha256"])
    assert "VERSION" in ignored
    assert ".toolkit-commit" in ignored
    assert ".toolkit-archive-sha256" in ignored
