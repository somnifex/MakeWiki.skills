"""Central lookup for toolkit tool instances."""

from __future__ import annotations

from makewiki_skills.toolkit.base import BaseTool

class ToolRegistry:
    """Singleton registry that holds references to tool instances."""

    _instance: ToolRegistry | None = None

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    @classmethod
    def instance(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (mainly for testing)."""
        cls._instance = None

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def has(self, name: str) -> bool:
        return name in self._tools
