"""Base types for the toolkit layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standardised return type for every tool operation."""

    success: bool
    data: Any = None
    error: str | None = None
    source_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BaseTool(Protocol):

    name: str

    def execute(self, **kwargs: Any) -> ToolResult: ...
