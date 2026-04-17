"""Tests for AST-based config access tracking and grep fallback."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.toolkit.config_access_tracker import ConfigAccessTracker


def test_tracks_nested_subscript_access(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text(
        "def run(config):\n    value = config['server']['port']\n    return value\n",
        encoding="utf-8",
    )

    tracker = ConfigAccessTracker()
    accesses = tracker.extract_from_file(source)
    key_paths = {access.key_path for access in accesses}

    assert "server.port" in key_paths
    assert "server" not in key_paths


def test_tracks_attribute_and_alias_access(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text(
        "def run(config):\n"
        "    server = config.server\n"
        "    return server.host\n",
        encoding="utf-8",
    )

    tracker = ConfigAccessTracker()
    accesses = tracker.extract_from_file(source)
    key_paths = {access.key_path for access in accesses}

    assert "server.host" in key_paths


def test_grep_fallback_marks_dynamic_access_low_confidence(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text(
        "def run(config, key_name):\n    return config[key_name]\n",
        encoding="utf-8",
    )

    tracker = ConfigAccessTracker()
    accesses = tracker.grep_fallback_from_file(source)

    assert any(access.key_path == "<dynamic>" for access in accesses)
    assert all(access.confidence == "low" for access in accesses)
