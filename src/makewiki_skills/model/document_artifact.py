"""Neutral document-artifact model shared across the Mechanical Plane.

This module is the single canonical home of the rendered-document value object
that every verifier, the site compiler, the revision engine and the writers all
consume. It deliberately lives in :mod:`makewiki_skills.model` — NOT inside the
legacy deterministic generator — so the verification core never depends on a
deprecated renderer's type (the Cognitive Authority Boundary invariant:
"verifiers must NOT import from the legacy generator").

``DocumentArtifact`` is the canonical name. ``GeneratedDocument`` is kept as a
backward-compatible alias so the many existing import sites keep working while
the codebase migrates to the neutral name.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class DocumentArtifact(BaseModel):
    """A single rendered Markdown document for one language.

    Pure value object: no logic, no generation side-effects. It is produced by
    the LLM Language Writer adapter and by the legacy deterministic renderer,
    and it is consumed by L0-L5 verifiers, the MechanicalRepairEngine, the
    cross-language reviewer, the output manager and the site compiler.
    """

    filename: str  # e.g. "README.md" or "README.zh-CN.md"
    base_name: str  # e.g. "README.md" (without language suffix)
    language_code: str
    content: str
    word_count: int = 0
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )


# Backward-compatible alias: consumers migrating from the legacy generator path
# can swap to DocumentArtifact and keep working. New code should use
# DocumentArtifact; the alias exists only to keep existing imports valid while
# the codebase is migrated.
GeneratedDocument = DocumentArtifact
