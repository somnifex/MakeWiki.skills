"""Read common project configuration formats into Python data."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from makewiki_skills.toolkit.base import ToolResult

class ConfigReaderTool:
    """Read and normalize project configuration files."""

    name = "config_reader"

    def read_yaml(self, path: Path) -> ToolResult:
        return self._read(path, self._parse_yaml)

    def read_toml(self, path: Path) -> ToolResult:
        return self._read(path, self._parse_toml)

    def read_json(self, path: Path) -> ToolResult:
        return self._read(path, self._parse_json)

    def read_env_file(self, path: Path) -> ToolResult:
        """Parse a .env / .env.example file into key-value pairs."""
        return self._read(path, self._parse_env)

    def read_ini(self, path: Path) -> ToolResult:
        return self._read(path, self._parse_ini)

    def read_any(self, path: Path) -> ToolResult:
        """Detect format from extension and delegate."""
        p = Path(path)
        ext = p.suffix.lower()
        name = p.name.lower()
        if ext in (".yaml", ".yml"):
            return self.read_yaml(p)
        if ext == ".toml":
            return self.read_toml(p)
        if ext == ".json":
            return self.read_json(p)
        if name.startswith(".env"):
            return self.read_env_file(p)
        if ext in (".ini", ".cfg"):
            return self.read_ini(p)
        return ToolResult(success=False, error=f"Unknown config format: {ext}")

    @staticmethod
    def extract_key_paths(data: dict[str, Any], prefix: str = "") -> list[str]:
        """Flatten a nested dict into dotted key paths."""
        paths: list[str] = []
        for key, value in data.items():
            full = f"{prefix}.{key}" if prefix else key
            paths.append(full)
            if isinstance(value, dict):
                paths.extend(ConfigReaderTool.extract_key_paths(value, full))
        return paths

    def _read(self, path: Path, parser: Any) -> ToolResult:
        try:
            real = Path(path).resolve()
            if not real.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            content = real.read_text(encoding="utf-8", errors="replace")
            data = parser(content)
            return ToolResult(success=True, data=data, source_path=str(real))
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    @staticmethod
    def _parse_yaml(text: str) -> Any:
        return yaml.safe_load(text) or {}

    @staticmethod
    def _parse_toml(text: str) -> Any:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]
        return tomllib.loads(text)

    @staticmethod
    def _parse_json(text: str) -> Any:
        return json.loads(text)

    @staticmethod
    def _parse_env(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
            if match:
                result[match.group(1)] = match.group(2).strip().strip("\"'")
        return result

    @staticmethod
    def _parse_ini(text: str) -> dict[str, dict[str, str]]:
        import configparser
        import io

        cp = configparser.ConfigParser()
        cp.read_file(io.StringIO(text))
        return {sec: dict(cp[sec]) for sec in cp.sections()}

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        if path is None:
            return ToolResult(success=False, error="path is required")
        return self.read_any(Path(path))
