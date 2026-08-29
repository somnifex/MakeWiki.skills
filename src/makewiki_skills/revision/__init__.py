"""Revision package for automated verification-to-revision loop."""

from __future__ import annotations

from makewiki_skills.revision.revision_engine import (
    MechanicalRepairEngine,
    RevisionAction,
    RevisionReport,
)

# Backwards-compatible alias: the semantic revision engine was renamed to the
# mechanical-only ``MechanicalRepairEngine``. New code should use the new name.
RevisionEngine = MechanicalRepairEngine

__all__ = [
    "MechanicalRepairEngine",
    "RevisionAction",
    "RevisionReport",
    "RevisionEngine",
]
