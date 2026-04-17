from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_URL = "https://github.com/somnifex/MakeWiki.skills.git"
ARCHIVE_URL = "https://github.com/somnifex/MakeWiki.skills/archive/refs/heads/main.zip"
REQUIRED_PATHS = (
    "pyproject.toml",
    "scripts/run_toolkit.py",
    "src/makewiki_skills/__init__.py",
)
FINGERPRINT_PATHS = (
    Path("pyproject.toml"),
    Path("uv.lock"),
    Path("scripts") / "run_toolkit.py",
    Path("src") / "makewiki_skills",
)
DEFAULT_SKILL_FILE = Path("skills") / "makewiki" / "SKILL.md"
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
VERSION_PATTERN = re.compile(r'^version:\s*["\']?(?P<version>[^"\']+)["\']?\s*$')
PYPROJECT_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*["\'](?P<version>[^"\']+)["\']\s*$')


@dataclass(frozen=True)
class BootstrapStatus:
    status: str
    toolkit_root: Path
    installed: bool
    source_kind: str | None
    source_root: Path | None
    installed_version: str | None
    candidate_version: str | None
    installed_fingerprint: str | None
    candidate_fingerprint: str | None
    update_available: bool
    update_reason: str | None

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "toolkit_root": str(self.toolkit_root),
            "installed": self.installed,
            "source_kind": self.source_kind,
            "source_root": str(self.source_root) if self.source_root is not None else None,
            "installed_version": self.installed_version,
            "candidate_version": self.candidate_version,
            "installed_fingerprint": self.installed_fingerprint,
            "candidate_fingerprint": self.candidate_fingerprint,
            "update_available": self.update_available,
            "update_reason": self.update_reason,
        }


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


def build_bootstrap_status(start: Path, target: Path | None = None) -> BootstrapStatus:
    resolved_target = (target or toolkit_root()).resolve()
    local_source = discover_local_source(start.resolve())
    source_root = local_source.resolve() if local_source is not None else None
    installed = looks_like_toolkit_root(resolved_target)
    installed_version = _read_skill_version(resolved_target) if installed else None
    installed_fingerprint = _fingerprint_toolkit(resolved_target) if installed else None
    candidate_version = _read_skill_version(source_root) if source_root is not None else None
    candidate_fingerprint = (
        _fingerprint_toolkit(source_root) if source_root is not None else None
    )

    update_available = False
    update_reason = None
    if (
        installed
        and source_root is not None
        and source_root != resolved_target
        and candidate_fingerprint is not None
        and candidate_fingerprint != installed_fingerprint
    ):
        update_available = True
        update_reason = _describe_update(installed_version, candidate_version)

    status = "missing"
    if installed:
        status = "update_available" if update_available else "ready"

    return BootstrapStatus(
        status=status,
        toolkit_root=resolved_target,
        installed=installed,
        source_kind="bundled_checkout" if source_root is not None else None,
        source_root=source_root,
        installed_version=installed_version,
        candidate_version=candidate_version,
        installed_fingerprint=installed_fingerprint,
        candidate_fingerprint=candidate_fingerprint,
        update_available=update_available,
        update_reason=update_reason,
    )


def ensure_home_toolkit(start: Path | None = None, update: bool = False) -> Path:
    target = toolkit_root()
    local_source = discover_local_source((start or Path(__file__).resolve()).resolve())
    if local_source is not None:
        if local_source.resolve() == target.resolve():
            return target
        if update or not looks_like_toolkit_root(target):
            if not target.resolve().is_relative_to(local_source.resolve()):
                replace_dir(target, local_source)
                return target
        if looks_like_toolkit_root(target):
            return target

    if looks_like_toolkit_root(target) and not update:
        return target

    if shutil.which("git"):
        try:
            populate_from_git(target)
            return target
        except subprocess.CalledProcessError:
            pass

    populate_from_archive(target)
    return target


def emit_status(status: BootstrapStatus, output_format: str = "human") -> None:
    payload = status.to_payload()
    if output_format == "json":
        print(json.dumps(payload, indent=2))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect or prepare the home-scoped MakeWiki toolkit.")
    subparsers = parser.add_subparsers(dest="command")

    status_parser = subparsers.add_parser("status", help="Inspect the installed toolkit and bundled source.")
    status_parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format.",
    )

    subparsers.add_parser("update", help="Sync the installed toolkit to the bundled checkout.")
    return parser.parse_args(argv)


def _read_skill_version(root: Path | None) -> str | None:
    if root is None:
        return None

    for candidate in (root / DEFAULT_SKILL_FILE, root / "SKILL.md", root / "pyproject.toml"):
        if not candidate.is_file():
            continue
        text = candidate.read_text(encoding="utf-8")
        if candidate.name == "pyproject.toml":
            return _match_first(PYPROJECT_VERSION_PATTERN, text)
        return _match_first(VERSION_PATTERN, text)
    return None


def _match_first(pattern: re.Pattern[str], text: str) -> str | None:
    for line in text.splitlines():
        match = pattern.match(line)
        if match is not None:
            return match.group("version").strip()
    return None


def _fingerprint_toolkit(root: Path | None) -> str | None:
    if root is None:
        return None
    files = list(_iter_fingerprint_files(root))
    if not files:
        return None

    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    return digest.hexdigest()[:12]


def _iter_fingerprint_files(root: Path) -> Iterable[Path]:
    files: list[Path] = []
    for relative_path in FINGERPRINT_PATHS:
        path = root / relative_path
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("*")):
                if candidate.is_file() and "__pycache__" not in candidate.relative_to(root).parts:
                    files.append(candidate)
    return files


def _describe_update(
    installed_version: str | None,
    candidate_version: str | None,
) -> str:
    if (
        installed_version is not None
        and candidate_version is not None
        and installed_version != candidate_version
    ):
        return (
            f"Installed toolkit version {installed_version} differs from bundled version "
            f"{candidate_version}."
        )
    return "Bundled toolkit files differ from the installed home toolkit."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    start = Path(__file__).resolve()
    try:
        if args.command == "status":
            emit_status(build_bootstrap_status(start, target=toolkit_root()), args.format)
            return 0
        if args.command == "update":
            print(ensure_home_toolkit(start=start, update=True))
            return 0
        print(ensure_home_toolkit(start=start))
        return 0
    except Exception as exc:
        if args.command == "status" and getattr(args, "format", "human") == "json":
            error_payload = {
                "status": "error",
                "toolkit_root": str(toolkit_root()),
                "installed": False,
                "source_kind": None,
                "source_root": None,
                "installed_version": None,
                "candidate_version": None,
                "installed_fingerprint": None,
                "candidate_fingerprint": None,
                "update_available": False,
                "update_reason": None,
                "error": str(exc),
            }
            print(json.dumps(error_payload, indent=2))
            return 1
        print("NOT_FOUND")
        sys.stderr.write(f"Failed to prepare {toolkit_root()}: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
