"""Tests for the LLM-authored DocumentationPlan validation model.

The DocumentationPlan is the Architect's page-structure handoff. Python only
validates the schema and serializes — it must never split pages, order
navigation, group personas, or infer pages from filenames. Tests confirm the
schema (including the ``relations[].from`` alias round-trip), strictness
(``extra="forbid"``), and that an empty plan is a valid, non-inferring artifact.
"""

import pytest
from pydantic import ValidationError

from makewiki_skills.model.documentation_plan import (
    DocumentationPlan,
    DocumentationRelation,
    DocumentationSection,
)


def _sample_plan() -> DocumentationPlan:
    return DocumentationPlan(
        sections=[
            DocumentationSection(
                id="admin-guide",
                title_intent="Administrator Guide",
                persona=["admin", "operator"],
                pages=[
                    "admin/channel-management",
                    "admin/channel-routing",
                ],
            )
        ],
        pages=["admin/channel-management", "management-api/channels"],
        relations=[
            DocumentationRelation(
                from_="admin/channel-management",
                to="management-api/channels",
                type="related",
            )
        ],
        rationale=[
            "Operator/admin pages come first; the reference is cross-linked.",
        ],
    )


def test_documentation_plan_serialization_round_trip():
    plan = _sample_plan()
    payload = plan.model_dump_json()
    rebuilt = DocumentationPlan.model_validate_json(payload)
    assert rebuilt == plan
    assert rebuilt.sections[0].id == "admin-guide"
    assert rebuilt.pages[0] == "admin/channel-management"
    assert rebuilt.relations[0].type == "related"


def test_documentation_plan_relations_from_alias_round_trip():
    """The authored ``relations[].from`` key maps onto ``from_`` and back."""
    plan = DocumentationPlan(
        relations=[{"from": "a", "to": "b", "type": "related"}]
    )
    assert plan.relations[0].from_ == "a"
    dumped = plan.model_dump(by_alias=True)
    assert dumped["relations"][0]["from"] == "a"
    assert "from_" not in dumped["relations"][0]


def test_documentation_plan_defaults_are_empty():
    """An authored plan with no entries validates as empty — Python infers nothing."""
    plan = DocumentationPlan()
    assert plan.sections == []
    assert plan.pages == []
    assert plan.relations == []
    assert plan.rationale == []


def test_documentation_plan_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate({"auto_split": True})
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {"sections": [{"id": "admin-guide", "inferred_persona": True}]}
        )
