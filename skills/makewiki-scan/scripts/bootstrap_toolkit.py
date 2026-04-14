from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/HowieWood/MakeWiki.skills.git"
ARCHIVE_URL = "https://github.com/HowieWood/MakeWiki.skills/archive/refs/heads/main.zip"
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


def populate_from_archive(target: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = Path(tmp_dir) / "makewiki-skills.zip"
        urllib.request.urlretrieve(ARCHIVE_URL, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(tmp_dir)
        extracted_root = next(
            (path for path in Path(tmp_dir).iterdir() if path.is_dir() and looks_like_toolkit_root(path)),
            None,
        )
        if extracted_root is None:
            raise RuntimeError("Unexpected archive layout")
        replace_dir(target, extracted_root)


def populate_from_git(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    subprocess.run(["git", "clone", "--depth", "1", REPO_URL, str(target)], check=True)


def ensure_home_toolkit() -> Path:
    target = toolkit_root()
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
            populate_from_git(target)
            return target
        except subprocess.CalledProcessError:
            pass

    populate_from_archive(target)
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
