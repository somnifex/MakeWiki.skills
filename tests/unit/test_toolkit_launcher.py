"""Tests for the repo-local toolkit launcher."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from makewiki_skills import toolkit_launcher


def build_test_context(tmp_path: Path) -> toolkit_launcher.LaunchContext:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\nversion = '0.1.0'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return toolkit_launcher.build_launch_context(tmp_path)


def test_toolkit_is_ready_requires_matching_state_and_import_probe(
    tmp_path: Path, monkeypatch
) -> None:
    context = build_test_context(tmp_path)
    context.python_path.parent.mkdir(parents=True, exist_ok=True)
    context.python_path.write_text("", encoding="utf-8")
    toolkit_launcher._write_state(context.state_file, toolkit_launcher.project_state(context.project_root))
    monkeypatch.setattr(toolkit_launcher, "_probe_toolkit_import", lambda _context: True)

    assert toolkit_launcher.toolkit_is_ready(context) is True


def test_ensure_toolkit_environment_prefers_uv(tmp_path: Path, monkeypatch) -> None:
    context = build_test_context(tmp_path)
    commands: list[list[str]] = []

    monkeypatch.setattr(toolkit_launcher, "toolkit_is_ready", lambda _context: False)
    monkeypatch.setattr(toolkit_launcher, "_probe_toolkit_import", lambda _context: True)
    monkeypatch.setattr(toolkit_launcher.shutil, "which", lambda _name: "uv")
    monkeypatch.setattr(
        toolkit_launcher,
        "_run_install",
        lambda command: commands.append([str(part) for part in command]),
    )

    python_path = toolkit_launcher.ensure_toolkit_environment(context)

    assert python_path == context.python_path
    assert commands[0] == ["uv", "venv", str(context.venv_dir), "--python", sys.executable]
    assert commands[1] == [
        "uv",
        "pip",
        "install",
        "--python",
        str(context.python_path),
        "-e",
        str(context.project_root),
    ]


def test_ensure_toolkit_environment_falls_back_to_venv_without_uv(
    tmp_path: Path, monkeypatch
) -> None:
    context = build_test_context(tmp_path)
    commands: list[list[str]] = []

    monkeypatch.setattr(toolkit_launcher, "toolkit_is_ready", lambda _context: False)
    monkeypatch.setattr(toolkit_launcher, "_probe_toolkit_import", lambda _context: True)
    monkeypatch.setattr(toolkit_launcher.shutil, "which", lambda _name: None)
    monkeypatch.setattr(
        toolkit_launcher,
        "_run_install",
        lambda command: commands.append([str(part) for part in command]),
    )

    python_path = toolkit_launcher.ensure_toolkit_environment(context)

    assert python_path == context.python_path
    assert commands[0] == [sys.executable, "-m", "venv", str(context.venv_dir)]
    assert commands[1] == [
        str(context.python_path),
        "-m",
        "pip",
        "install",
        "-e",
        str(context.project_root),
    ]


def test_main_dispatches_to_repo_local_python(tmp_path: Path, monkeypatch) -> None:
    context = build_test_context(tmp_path)
    fake_python = context.project_root / ".venv" / "Scripts" / "python.exe"
    captured: list[list[str]] = []

    monkeypatch.setattr(
        toolkit_launcher,
        "ensure_toolkit_environment",
        lambda _context: fake_python,
    )

    def fake_run(command: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
        captured.append(command)
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(toolkit_launcher.subprocess, "run", fake_run)

    exit_code = toolkit_launcher.main(
        args=["scan", ".", "--format", "json"],
        project_root=context.project_root,
    )

    assert exit_code == 7
    assert captured == [[str(fake_python), "-m", "makewiki_skills", "scan", ".", "--format", "json"]]
