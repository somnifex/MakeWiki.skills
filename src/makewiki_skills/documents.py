"""Shared document model for assembled Markdown output."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class GeneratedDocument(BaseModel):
    """A single rendered Markdown document for one language."""

    filename: str
    base_name: str
    language_code: str
    content: str
    word_count: int = 0
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
