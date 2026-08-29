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
DEFAULT_VERSION = "2.0.0"
IGNORED_SHA256_MSG = "MAKEWIKI_TOOLKIT_SHA256 unset; skipping archive integrity check"
REQUIRED_PATHS = (
    "pyproject.toml",
    "scripts/run_toolkit.py",
    "src/makewiki_skills/__init__.py",
)
IGNORE = shutil.ignore_patterns(
    ".git",
    ".history",
    ".makewiki",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
)


def requested_version() -> str:
    """Resolve the toolkit version, from env or the bundled default.

    ``MAKEWIKI_TOOLKIT_VERSION`` pins the exact skill↔toolkit pair. When unset,
    fall back to the version this repo is currently developed at.
    """
    return os.environ.get("MAKEWIKI_TOOLKIT_VERSION", DEFAULT_VERSION).lstrip("v")


def requested_sha256() -> str | None:
    """Return the expected SHA256 of the archive, or None when not pinned."""
    value = os.environ.get("MAKEWIKI_TOOLKIT_SHA256", "").strip().lower()
    return value or None


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


def populate_from_git(target: Path, version: str, expected_sha256: str | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    tag = f"v{version.lstrip('v')}"
    print(f"Cloning {git_clone_url()} at tag {tag}")
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", tag, git_clone_url(), str(target)],
        check=True,
    )
    if expected_sha256:
        verify_git_checkout_sha256(target, expected_sha256)


def verify_git_checkout_sha256(root: Path, expected: str) -> None:
    """Best-effort integrity marker for git clones.

    A git clone has no single archive to hash, so we hash the tree as a
    deterministic marker (sorted relative paths + file bytes). This is a
    supplementary integrity signal on top of git's own tag+commit pinning.
    """
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    actual = digest.hexdigest()
    if actual != expected:
        raise RuntimeError(
            f"Toolkit tree SHA256 mismatch for {root}: expected {expected}, got {actual}"
        )


def ensure_home_toolkit() -> Path:
    target = toolkit_root()
    version = requested_version()
    expected_sha256 = requested_sha256()
    local_source = discover_local_source(Path(__file__).resolve())
    if local_source is not None:
        if local_source.resolve() == target.resolve():
            return target
        if not target.resolve().is_relative_to(local_source.resolve()):
            replace_dir(target, local_source)
            return target

    if looks_like_toolkit_root(target):
        return target

    if shutil.which("git"):
        try:
            populate_from_git(target, version)
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
