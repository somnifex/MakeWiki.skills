"""Bootstrap Reproducibility Contract.

The root ``scripts/bootstrap_toolkit.py`` is the canonical version-pinned +
SHA256-checked bootstrap: it resolves an exact release tag
(``archive/refs/tags/v2.0.0.zip`` / ``--branch v2.0.0``) and verifies an
archive SHA256 when ``MAKEWIKI_TOOLKIT_SHA256`` is set. Every subskill ships a
copy of this script so each phase self-bootstraps identically.

The contract guards against supply-chain drift: it forbids any subskill copy
from silently reverting to the old behaviour of pulling an unpinned
``archive/refs/heads/main`` archive or an unversioned ``git clone`` of
``main`` (no checksum, moving target).
"""

from __future__ import annotations

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


def test_root_bootstrap_carries_version_and_sha256_pinning():
    """The canonical root script must pin the version and support SHA256 checks."""
    text = ROOT_BOOTSTRAP.read_text(encoding="utf-8")
    assert "MAKEWIKI_TOOLKIT_VERSION" in text, (
        "root bootstrap must resolve version from MAKEWIKI_TOOLKIT_VERSION"
    )
    assert "MAKEWIKI_TOOLKIT_SHA256" in text, (
        "root bootstrap must support the MAKEWIKI_TOOLKIT_SHA256 archive integrity check"
    )
    assert "refs/heads/main" not in text, (
        "root bootstrap must never pull the moving main branch"
    )
