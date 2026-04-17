"""Tests for skill bootstrap update detection and sync behavior."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
BOOTSTRAP_SCRIPT = SKILLS_DIR / "makewiki" / "scripts" / "bootstrap_toolkit.py"


def load_bootstrap_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("makewiki_bootstrap_toolkit", BOOTSTRAP_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fake_toolkit(root: Path, *, skill_version: str, runtime_marker: str) -> Path:
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "src" / "makewiki_skills").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "makewiki" / "scripts").mkdir(parents=True, exist_ok=True)

    (root / "pyproject.toml").write_text(
        '[project]\nname = "makewiki-skills"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (root / "uv.lock").write_text(f"# {runtime_marker}\n", encoding="utf-8")
    (root / "scripts" / "run_toolkit.py").write_text(
        f'RUNTIME_MARKER = "{runtime_marker}"\n',
        encoding="utf-8",
    )
    (root / "src" / "makewiki_skills" / "__init__.py").write_text(
        '__version__ = "0.1.0"\n',
        encoding="utf-8",
    )
    (root / "src" / "makewiki_skills" / "runtime_marker.py").write_text(
        f'VALUE = "{runtime_marker}"\n',
        encoding="utf-8",
    )
    (root / "skills" / "makewiki" / "SKILL.md").write_text(
        f'---\nname: makewiki\nversion: "{skill_version}"\n---\n',
        encoding="utf-8",
    )
    bootstrap_script = root / "skills" / "makewiki" / "scripts" / "bootstrap_toolkit.py"
    bootstrap_script.write_text("# bootstrap placeholder\n", encoding="utf-8")
    return bootstrap_script


def test_build_bootstrap_status_reports_update_available(tmp_path: Path) -> None:
    module = load_bootstrap_module()
    source_script = write_fake_toolkit(
        tmp_path / "source",
        skill_version="0.6.2",
        runtime_marker="new",
    )
    installed_root = tmp_path / "home" / ".makewiki"
    write_fake_toolkit(
        installed_root,
        skill_version="0.6.2",
        runtime_marker="old",
    )

    status = module.build_bootstrap_status(source_script, target=installed_root)

    assert status.status == "update_available"
    assert status.installed is True
    assert status.update_available is True
    assert status.source_kind == "bundled_checkout"
    assert status.source_root == (tmp_path / "source").resolve()
    assert status.installed_version == "0.6.2"
    assert status.candidate_version == "0.6.2"
    assert status.installed_fingerprint != status.candidate_fingerprint


def test_ensure_home_toolkit_keeps_existing_install_without_update_flag(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_bootstrap_module()
    source_script = write_fake_toolkit(
        tmp_path / "source",
        skill_version="0.6.2",
        runtime_marker="new",
    )
    installed_root = tmp_path / "home" / ".makewiki"
    write_fake_toolkit(
        installed_root,
        skill_version="0.6.2",
        runtime_marker="old",
    )
    monkeypatch.setattr(module, "toolkit_root", lambda: installed_root)

    result = module.ensure_home_toolkit(start=source_script, update=False)

    assert result == installed_root
    assert (
        installed_root / "src" / "makewiki_skills" / "runtime_marker.py"
    ).read_text(encoding="utf-8") == 'VALUE = "old"\n'


def test_ensure_home_toolkit_update_replaces_existing_install(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = load_bootstrap_module()
    source_script = write_fake_toolkit(
        tmp_path / "source",
        skill_version="0.6.2",
        runtime_marker="new",
    )
    installed_root = tmp_path / "home" / ".makewiki"
    write_fake_toolkit(
        installed_root,
        skill_version="0.6.2",
        runtime_marker="old",
    )
    monkeypatch.setattr(module, "toolkit_root", lambda: installed_root)

    result = module.ensure_home_toolkit(start=source_script, update=True)

    assert result == installed_root
    assert (
        installed_root / "src" / "makewiki_skills" / "runtime_marker.py"
    ).read_text(encoding="utf-8") == 'VALUE = "new"\n'
    assert (installed_root / "skills" / "makewiki" / "SKILL.md").read_text(
        encoding="utf-8"
    ).startswith('---\nname: makewiki\nversion: "0.6.2"')
