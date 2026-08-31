"""SemanticModel Boundary Contract: V3 page planning is fed by DocumentationModel.

The SemanticModel historically mixed "what the software is" with documentation
semantics (``user_tasks``, ``usage_examples``, ``faq``, ``troubleshooting``,
``command_groups``). V3 resolves that dual authority by making the
``DocumentationModel`` the canonical audience/goal input to Page Planning, while
the legacy SemanticModel documentation fields remain only for V2 serialization
compatibility (see ``references/v3/DOCUMENTATION_MODEL.md`` and the V2-compat
docstring on ``SemanticModel``).

This contract pins two things so a future change cannot silently re-introduce
the dual authority:

1. **Positive**: Page Planning's documented authoritative input is the
   ``DocumentationModel`` (which yields ``DocumentationPlan`` + ``PageSpec``s).
2. **Negative**: the authoritative planning docs never present a legacy
   SemanticModel documentation field as the direct source of V3 ``PageSpec``s.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

#: The documentation fields on SemanticModel that are V2-compatibility only and
#: are NOT the canonical input to V3 page planning.
LEGACY_DOC_FIELDS = (
    "user_tasks",
    "usage_examples",
    "faq",
    "troubleshooting",
    "command_groups",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _authoritative_planning_text() -> str:
    """The planning-authority docs: SKILL.md plus every task and references/v3 doc.

    Everything the LLM-orchestrated flow treats as authoritative for planning and
    writing. Page Planning consumes this corpus when deciding what a Writer sees.
    """
    parts: list[str] = []
    skill = PROJECT_ROOT / "SKILL.md"
    if skill.is_file():
        parts.append(_read(skill))
    tasks_dir = PROJECT_ROOT / "tasks"
    for p in sorted(tasks_dir.glob("*.md")):
        parts.append(_read(p))
    refs_dir = PROJECT_ROOT / "references" / "v3"
    for p in sorted(refs_dir.glob("*.md")):
        parts.append(_read(p))
    return "\n".join(parts)


def test_page_planning_authoritative_input_is_documentation_model():
    """Page Planning names DocumentationModel (and its Plan/PageSpec products) as
    the authoritative input; it is not fed by a legacy SemanticModel doc field."""
    planning = _read(PROJECT_ROOT / "tasks" / "plan-pages.md")
    modeling = _read(PROJECT_ROOT / "tasks" / "document-model.md")

    assert "DocumentationModel" in planning, (
        "tasks/plan-pages.md must name DocumentationModel as the authoritative input"
    )
    assert "DocumentationPlan" in planning and "PageSpec" in planning
    assert "DocumentationModel" in modeling

    # The documented page-planning input chain must be DocumentationModel ->
    # DocumentationPlan -> PageSpec[], not a legacy field chain.
    chain_ok = (
        "DocumentationModel" in planning
        and "DocumentationPlan" in planning
        and "PageSpec" in planning
    )
    assert chain_ok


def test_legacy_semanticmodel_doc_fields_are_not_pageplanning_authority():
    """No authoritative doc may declare that a legacy SemanticModel documentation
    field *directly decides* V3 PageSpecs / pages / page splits.

    That phrasing is the smoking gun of the dual authority PHASE E removes. The
    legacy fields may legitimately appear (as page-type vocabulary, as
    SemanticModel inputs to Documentation Modeling, or as V2-compat notes), but
    they must never be stated as the producer of the page set.
    """
    authoritative = _authoritative_planning_text()

    # Dangerous coupling: "<legacy field> (->) decide/determine/drive/dictate/
    # produce/generate/map to <pages|PageSpecs|page split>". Only genuine dual
    # authority would phrase it this way in the planning/writing corpus.
    dangerous = re.compile(
        r"(?P<field>user_tasks|usage_examples|command_groups|faq|troubleshooting)"
        r"[^\n.]{0,40}?"
        r"(?:\bdecide|\bdetermine|\bdrive|\bdictate|\bproduce|\bgenerate|\bmap\s+to)"
        r"[^\n.]{0,40}?"
        r"(?:\bpages?\b|\bPageSpecs?\b|\bpage\s+split\b)",
        re.IGNORECASE,
    )
    hits = [m.group(0).strip() for m in dangerous.finditer(authoritative)]
    assert not hits, (
        "Plan docs must not present a legacy SemanticModel doc field as the direct "
        "authority for V3 PageSpecs (PHASE E removes this dual authority); found: "
        + "; ".join(sorted(set(hits)))
    )
