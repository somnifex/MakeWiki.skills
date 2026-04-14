"""Discover user-facing commands from build files without executing them."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.toolkit.base import ToolResult

class MakeTarget(BaseModel):
    """A target parsed from a Makefile."""

    name: str
    dependencies: list[str] = Field(default_factory=list)
    description: str | None = None
    body: str = ""

class ScriptEntry(BaseModel):
    """A script entry from package.json / pyproject.toml."""

    name: str
    command: str
    source: str  # "package_json" | "pyproject_scripts" | "makefile"
    description: str | None = None

class CommandProbeTool:
    """Parse build metadata to discover commands without executing them."""

    name = "command_probe"

    def parse_makefile(self, path: Path) -> ToolResult:
        try:
            real = Path(path).resolve()
            if not real.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            content = real.read_text(encoding="utf-8", errors="replace")
            targets = self._extract_make_targets(content)
            return ToolResult(
                success=True,
                data={"targets": [t.model_dump() for t in targets]},
                source_path=str(real),
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def _extract_make_targets(self, content: str) -> list[MakeTarget]:
        targets: list[MakeTarget] = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            match = re.match(r"^([a-zA-Z_][\w.-]*):\s*(.*)?$", line)
            if match:
                name = match.group(1)
                deps = match.group(2).split() if match.group(2) else []
                desc = None
                if "##" in line:
                    desc = line.split("##", 1)[1].strip()
                elif i > 0 and lines[i - 1].strip().startswith("##"):
                    desc = lines[i - 1].strip().lstrip("#").strip()
                body_lines: list[str] = []
                j = i + 1
                while j < len(lines) and lines[j].startswith("\t"):
                    body_lines.append(lines[j][1:])
                    j += 1
                targets.append(
                    MakeTarget(
                        name=name,
                        dependencies=deps,
                        description=desc,
                        body="\n".join(body_lines),
                    )
                )
                i = j
            else:
                i += 1
        return targets

    def parse_package_json_scripts(self, path: Path) -> ToolResult:
        try:
            real = Path(path).resolve()
            if not real.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            data = json.loads(real.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if not isinstance(scripts, dict):
                scripts = {}
            entries = [
                ScriptEntry(name=str(k), command=str(v), source="package_json").model_dump()
                for k, v in scripts.items()
            ]
            return ToolResult(success=True, data={"scripts": entries}, source_path=str(real))
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def parse_pyproject_scripts(self, path: Path) -> ToolResult:
        try:
            real = Path(path).resolve()
            if not real.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            data = tomllib.loads(real.read_text(encoding="utf-8"))
            project_data = data.get("project", {})
            scripts = project_data.get("scripts", {}) if isinstance(project_data, dict) else {}
            if not isinstance(scripts, dict):
                scripts = {}
            entries = [
                ScriptEntry(name=str(k), command=str(v), source="pyproject_scripts").model_dump()
                for k, v in scripts.items()
            ]
            return ToolResult(success=True, data={"scripts": entries}, source_path=str(real))
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def detect_available_commands(self, project_dir: Path) -> ToolResult:
        """Scan common locations for user-facing commands."""
        root = Path(project_dir).resolve()
        all_entries: list[dict[str, Any]] = []

        makefile = root / "Makefile"
        if makefile.is_file():
            r = self.parse_makefile(makefile)
            if r.success:
                for t in r.data["targets"]:
                    all_entries.append(
                        ScriptEntry(
                            name=f"make {t['name']}",
                            command=t.get("body", ""),
                            source="makefile",
                            description=t.get("description"),
                        ).model_dump()
                    )

        pkg_json = root / "package.json"
        if pkg_json.is_file():
            r = self.parse_package_json_scripts(pkg_json)
            if r.success:
                all_entries.extend(r.data["scripts"])

        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            r = self.parse_pyproject_scripts(pyproject)
            if r.success:
                all_entries.extend(r.data["scripts"])

        return ToolResult(success=True, data={"commands": all_entries})

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path") or kwargs.get("project_dir")
        if path is None:
            return ToolResult(success=False, error="path or project_dir is required")
        return self.detect_available_commands(Path(path))
