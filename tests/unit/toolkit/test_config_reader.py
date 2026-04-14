"""Tests for ConfigReaderTool."""

from pathlib import Path

from makewiki_skills.toolkit.config_reader import ConfigReaderTool


def test_read_yaml(tmp_path: Path):
    f = tmp_path / "config.yaml"
    f.write_text("server:\n  host: localhost\n  port: 8080\n", encoding="utf-8")

    tool = ConfigReaderTool()
    result = tool.read_yaml(f)
    assert result.success
    assert result.data["server"]["host"] == "localhost"
    assert result.data["server"]["port"] == 8080


def test_read_json(tmp_path: Path):
    f = tmp_path / "config.json"
    f.write_text('{"name": "test", "version": "1.0"}', encoding="utf-8")

    tool = ConfigReaderTool()
    result = tool.read_json(f)
    assert result.success
    assert result.data["name"] == "test"


def test_read_env_file(tmp_path: Path):
    f = tmp_path / ".env"
    f.write_text("HOST=localhost\nPORT=8080\n# comment\nDEBUG=true\n", encoding="utf-8")

    tool = ConfigReaderTool()
    result = tool.read_env_file(f)
    assert result.success
    assert result.data["HOST"] == "localhost"
    assert result.data["PORT"] == "8080"
    assert result.data["DEBUG"] == "true"


def test_read_toml(tmp_path: Path):
    f = tmp_path / "config.toml"
    f.write_text('[project]\nname = "hello"\nversion = "0.1.0"\n', encoding="utf-8")

    tool = ConfigReaderTool()
    result = tool.read_toml(f)
    assert result.success
    assert result.data["project"]["name"] == "hello"


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
