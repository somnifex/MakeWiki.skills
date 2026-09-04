from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/somnifex/MakeWiki.skills.git"
DEFAULT_VERSION = "3.0.0"
# Provenance env vars. Version pins the skill↔toolkit pair; commit pins the Git
# identity; archive SHA256 is the archive integrity checksum. These are kept
# distinct — a checksum is NOT a Git identity.
VERSION_ENV = "MAKEWIKI_TOOLKIT_VERSION"
COMMIT_ENV = "MAKEWIKI_TOOLKIT_COMMIT"
ARCHIVE_SHA256_ENV = "MAKEWIKI_TOOLKIT_ARCHIVE_SHA256"
# Legacy combined name that conflated the Git identity with the archive
# checksum. Kept as a deprecated compatibility alias for one release cycle;
# reading it warns but does not error.
LEGACY_SHA256_ENV = "MAKEWIKI_TOOLKIT_SHA256"
LEGACY_SHA256_WARNING = (
    "MAKEWIKI_TOOLKIT_SHA256 is deprecated; use MAKEWIKI_TOOLKIT_ARCHIVE_SHA256 "
    "for the archive integrity checksum"
)
IGNORED_SHA256_MSG = "MAKEWIKI_TOOLKIT_ARCHIVE_SHA256 unset; skipping archive integrity check"
REQUIRED_PATHS = (
    "pyproject.toml",
    "scripts/run_toolkit.py",
    "src/makewiki_skills/__init__.py",
)
# Marker files recording the installed version and its provenance. These record
# the state of an *installation*, not of a source tree, so they must never be
# copied from a local source into a fresh install.
VERSION_FILE = "VERSION"
GIT_COMMIT_FILE = ".toolkit-commit"
ARCHIVE_SHA256_FILE = ".toolkit-archive-sha256"
IGNORE = shutil.ignore_patterns(
    ".git",
    ".history",
    ".makewiki",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    VERSION_FILE,
    GIT_COMMIT_FILE,
    ARCHIVE_SHA256_FILE,
)


def requested_version() -> str:
    """Resolve the toolkit version, from env or the bundled default.

    ``MAKEWIKI_TOOLKIT_VERSION`` pins the exact skill↔toolkit pair. When unset,
    fall back to the version this repo is currently developed at.
    """
    return os.environ.get(VERSION_ENV, DEFAULT_VERSION).lstrip("v")


def requested_commit() -> str | None:
    """Return the Git commit identity to pin, or None when not specified.

    ``MAKEWIKI_TOOLKIT_COMMIT`` pins the exact Git commit; it is distinct from
    the archive integrity checksum (``MAKEWIKI_TOOLKIT_ARCHIVE_SHA256``).
    """
    value = os.environ.get(COMMIT_ENV, "").strip()
    return value or None


def requested_archive_sha256() -> str | None:
    """Return the expected SHA256 of the archive, or None when not pinned.

    Reads ``MAKEWIKI_TOOLKIT_ARCHIVE_SHA256`` (the archive integrity checksum).
    Falls back to the legacy ``MAKEWIKI_TOOLKIT_SHA256`` name for one release
    cycle with a warning when the deprecated name is consumed — warn, never
    error, so old callers keep working while migrating.
    """
    value = os.environ.get(ARCHIVE_SHA256_ENV, "").strip().lower()
    if value:
        return value
    legacy = os.environ.get(LEGACY_SHA256_ENV, "").strip().lower()
    if legacy:
        print(LEGACY_SHA256_WARNING)
        return legacy
    return None


def requested_sha256() -> str | None:
    """Deprecated alias of :func:`requested_archive_sha256`.

    Retained so existing callers/tests of the pre-split name keep working; it
    returns the modern archive checksum (or the deprecated alias value).
    """
    return requested_archive_sha256()


def tag_archive_url(version: str) -> str:
    """GitHub archive zip for an exact release tag (never moving ``main``)."""
    tag = f"v{version.lstrip('v')}"
    return f"https://github.com/somnifex/MakeWiki.skills/archive/refs/tags/{tag}.zip"


def git_clone_url(branch: str | None = None) -> str:
    """Repository URL; callers pass ``--branch`` for an exact tag."""
    return REPO_URL


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive_sha256(archive_path: Path, expected: str | None) -> None:
    if not expected:
        print(IGNORED_SHA256_MSG)
        return
    actual = sha256_of_file(archive_path)
    if actual != expected:
        raise RuntimeError(
            f"SHA256 mismatch for {archive_path.name}: expected {expected}, got {actual}"
        )


def toolkit_root() -> Path:
    return Path.home() / ".makewiki"


def looks_like_toolkit_root(path: Path) -> bool:
    return all((path / relative_path).exists() for relative_path in REQUIRED_PATHS)


def installed_version(target: Path) -> str | None:
    """Return the version recorded in ``<root>/VERSION``, or None when absent."""
    marker = target / VERSION_FILE
    if not marker.is_file():
        return None
    value = marker.read_text(encoding="utf-8").strip()
    return value or None


def record_version(target: Path, version: str) -> None:
    """Persist the resolved version marker inside the toolkit install root."""
    target.mkdir(parents=True, exist_ok=True)
    (target / VERSION_FILE).write_text(f"{version}\n", encoding="utf-8")


def record_commit(target: Path, commit: str) -> None:
    """Persist the exact fetched git commit SHA for a git install."""
    target.mkdir(parents=True, exist_ok=True)
    (target / GIT_COMMIT_FILE).write_text(f"{commit}\n", encoding="utf-8")


def record_archive_sha256(target: Path, archive_sha256: str | None) -> None:
    """Persist the verified archive checksum for an archive install.

    Distinct from the git-commit record: archive installs carry a checksum of
    the downloaded zip, not a git identity. When ``archive_sha256`` is None any
    stale record is removed (nothing was verified).
    """
    target.mkdir(parents=True, exist_ok=True)
    marker = target / ARCHIVE_SHA256_FILE
    if archive_sha256:
        marker.write_text(f"{archive_sha256}\n", encoding="utf-8")
    elif marker.exists():
        marker.unlink()


def needs_replacement(target: Path, requested: str) -> bool:
    """True when the installed toolkit must be rebuilt for ``requested``.

    The tool is reused only when an install exists AND its recorded version
    matches the requested one. A wrong/stale (or absent) recorded version means
    the install is replaced.
    """
    if not looks_like_toolkit_root(target):
        return True
    return installed_version(target) != requested


def discover_local_source(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if looks_like_toolkit_root(candidate):
            return candidate
    return None


def replace_dir(target: Path, source: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=IGNORE)


def populate_from_archive(target: Path, version: str, expected_sha256: str | None) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = Path(tmp_dir) / "makewiki-skills.zip"
        archive_url = tag_archive_url(version)
        print(f"Downloading {archive_url}")
        urllib.request.urlretrieve(archive_url, archive_path)
        verify_archive_sha256(archive_path, expected_sha256)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(tmp_dir)
        extracted_root = next(
            (
                path
                for path in Path(tmp_dir).iterdir()
                if path.is_dir() and looks_like_toolkit_root(path)
            ),
            None,
        )
        if extracted_root is None:
            raise RuntimeError("Unexpected archive layout")
        replace_dir(target, extracted_root)
        record_version(target, version)
        verified_sha256 = expected_sha256 or sha256_of_file(archive_path)
        record_archive_sha256(target, verified_sha256)


def populate_from_git(
    target: Path,
    version: str,
    commit: str | None = None,
) -> None:
    """Install the toolkit from a pinned Git tag (version + optional commit).

    A Git install is verified by its Git identity only: the exact release tag
    (``--branch v<version>``) and, when pinned, the exact commit SHA. It is a
    hard boundary that a Git checkout is NEVER verified against an archive
    checksum — ``MAKEWIKI_TOOLKIT_ARCHIVE_SHA256`` is the integrity checksum for
    the downloaded release zip, not a property of a validated git checkout.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    tag = f"v{version.lstrip('v')}"
    print(f"Cloning {git_clone_url()} at tag {tag}")
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", tag, git_clone_url(), str(target)],
        check=True,
    )
    if commit:
        print(f"Pinning git install to commit {commit}")
        subprocess.run(
            ["git", "-C", str(target), "checkout", commit],
            check=True,
        )
    # Record the exact fetched commit SHA (git identity) — kept separate from
    # the archive checksum used for zip installs.
    fetched = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    record_commit(target, fetched)
    record_version(target, version)


def ensure_home_toolkit() -> Path:
    target = toolkit_root()
    version = requested_version()
    expected_sha256 = requested_archive_sha256()
    commit = requested_commit()
    local_source = discover_local_source(Path(__file__).resolve())
    if local_source is not None:
        if local_source.resolve() == target.resolve():
            return target
        if not target.resolve().is_relative_to(local_source.resolve()):
            replace_dir(target, local_source)
            record_version(target, version)
            return target

    # Reuse only when an install exists AND its recorded version matches the
    # requested one; a stale/absent version means replace.
    if not needs_replacement(target, version):
        return target

    if shutil.which("git"):
        try:
            # Git install verifies by version + commit identity only — never by
            # the archive checksum (expected_sha256 is for zip installs).
            populate_from_git(target, version, commit)
            return target
        except subprocess.CalledProcessError:
            pass

    populate_from_archive(target, version, expected_sha256)
    return target


def main() -> int:
    try:
        print(ensure_home_toolkit())
        return 0
    except Exception as exc:
        print("NOT_FOUND")
        sys.stderr.write(f"Failed to prepare {toolkit_root()}: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
