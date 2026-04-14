"""Launcher for invoking the internal toolkit from skill docs."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

MIN_PYTHON = (3, 11)
STATE_FILENAME = ".makewiki-toolkit-state.json"
TOOLKIT_PROBE = (
    "import pathlib, sys; "
    "import makewiki_skills; "
    "root = pathlib.Path(sys.argv[1]).resolve(); "
    "module_path = pathlib.Path(makewiki_skills.__file__).resolve(); "
    "raise SystemExit(0 if module_path.is_relative_to(root / 'src') else 1)"
)


@dataclass(frozen=True)
class LaunchContext:
    """Computed paths for the source checkout and home-scoped toolkit environment."""

    project_root: Path
    toolkit_root: Path
    venv_dir: Path
    python_path: Path
    state_file: Path


def default_toolkit_root() -> Path:
    """Return the default cross-platform toolkit root under the user's home directory."""
    return Path.home() / ".makewiki"


def build_launch_context(project_root: Path, toolkit_root: Path | None = None) -> LaunchContext:
    """Build the filesystem context for the launcher."""
    root = project_root.resolve()
    home_root = (toolkit_root or default_toolkit_root()).resolve()
    venv_dir = home_root / ".venv"
    python_path = venv_python_path(venv_dir)
    state_file = venv_dir / STATE_FILENAME
    return LaunchContext(
        project_root=root,
        toolkit_root=home_root,
        venv_dir=venv_dir,
        python_path=python_path,
        state_file=state_file,
    )


def venv_python_path(venv_dir: Path) -> Path:
    """Return the interpreter path inside a virtual environment."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def project_state(project_root: Path) -> dict[str, Any]:
    """Fingerprint the project metadata that should invalidate the launcher cache."""
    root = project_root.resolve()
    return {
        "schema_version": 1,
        "project_root": str(root),
        "pyproject_mtime_ns": _mtime_ns(root / "pyproject.toml"),
        "uv_lock_mtime_ns": _mtime_ns(root / "uv.lock"),
    }


def toolkit_is_ready(context: LaunchContext) -> bool:
    """Return True when the home-scoped venv already points at this project."""
    if not context.python_path.is_file():
        return False

    state = _read_state(context.state_file)
    if state != project_state(context.project_root):
        return False

    return _probe_toolkit_import(context)


def ensure_toolkit_environment(context: LaunchContext) -> Path:
    """Create or refresh the home-scoped venv, then return its Python executable."""
    if toolkit_is_ready(context):
        return context.python_path

    if shutil.which("uv"):
        try:
            _install_with_uv(context)
        except subprocess.CalledProcessError:
            _install_with_venv(context)
    else:
        _install_with_venv(context)

    if not _probe_toolkit_import(context):
        raise RuntimeError(
            f"Failed to bootstrap MakeWiki toolkit in {context.venv_dir}. "
            "The home-scoped environment was created, but makewiki_skills is still not importable."
        )

    _write_state(context.state_file, project_state(context.project_root))
    return context.python_path


def dispatch_to_toolkit(python_path: Path, args: Sequence[str]) -> int:
    """Run the internal CLI inside the home-scoped environment."""
    command = [str(python_path), "-m", "makewiki_skills", *args]
    result = subprocess.run(command, check=False)
    return result.returncode


def main(
    args: Sequence[str] | None = None,
    project_root: Path | None = None,
    toolkit_root: Path | None = None,
) -> int:
    """Entry point for the thin launcher script used by SKILL.md files."""
    argv = list(args if args is not None else sys.argv[1:])
    root = project_root.resolve() if project_root is not None else Path(__file__).resolve().parents[2]
    context = build_launch_context(root, toolkit_root=toolkit_root)
    python_path = ensure_toolkit_environment(context)
    return dispatch_to_toolkit(python_path, argv)


def _install_with_uv(context: LaunchContext) -> None:
    python_request = _preferred_python_request()
    if not context.python_path.is_file():
        _run_install(["uv", "venv", str(context.venv_dir), "--python", python_request])

    install_command = [
        "uv",
        "pip",
        "install",
        "--python",
        str(context.python_path),
        "-e",
        str(context.project_root),
    ]
    _run_install(install_command)


def _install_with_venv(context: LaunchContext) -> None:
    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        raise RuntimeError(
            "MakeWiki.skills needs Python "
            f"{required}+ when bootstrapping without uv, but the current interpreter is {current}."
        )

    _run_install([sys.executable, "-m", "venv", str(context.venv_dir)])
    _run_install([str(context.python_path), "-m", "pip", "install", "-e", str(context.project_root)])


def _preferred_python_request() -> str:
    if sys.version_info >= MIN_PYTHON:
        return sys.executable
    return ".".join(str(part) for part in MIN_PYTHON)


def _run_install(command: Sequence[str]) -> None:
    result = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return

    if result.stdout:
        sys.stderr.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)

    raise subprocess.CalledProcessError(
        result.returncode,
        list(command),
        output=result.stdout,
        stderr=result.stderr,
    )


def _probe_toolkit_import(context: LaunchContext) -> bool:
    command = [str(context.python_path), "-c", TOOLKIT_PROBE, str(context.project_root)]
    result = subprocess.run(
        command,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _read_state(state_file: Path) -> dict[str, Any] | None:
    if not state_file.is_file():
        return None

    try:
        raw = state_file.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    if isinstance(data, dict):
        return data
    return None


def _write_state(state_file: Path, state: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, sort_keys=True)
    state_file.write_text(payload + "\n", encoding="utf-8")


def _mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return 0
