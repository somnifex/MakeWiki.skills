"""Tests for ConfigReaderTool."""

from pathlib import Path

from makewiki_skills.toolkit.config_reader import ConfigReaderTool


def test_read_any_autodetect(tmp_path: Path):
    f = tmp_path / "settings.yaml"
    f.write_text("key: value\n", encoding="utf-8")

    tool = ConfigReaderTool()
    result = tool.read_any(f)
    assert result.success
    assert result.data["key"] == "value"


def test_extract_key_paths():
    data = {"server": {"host": "localhost", "port": 8080}, "debug": True}
    paths = ConfigReaderTool.extract_key_paths(data)
    assert "server" in paths
    assert "server.host" in paths
    assert "server.port" in paths
    assert "debug" in paths


def test_read_nonexistent(tmp_path: Path):
    tool = ConfigReaderTool()
    result = tool.read_yaml(tmp_path / "nope.yaml")
    assert not result.success
