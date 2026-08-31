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
    plan_page_consistency_errors,
)
from makewiki_skills.model.page_spec import PageSpec


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


def test_documentation_section_rejects_blank_id():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {"sections": [{"id": "  ", "title_intent": "Guide"}]}
        )


def test_documentation_section_rejects_blank_title_intent():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {"sections": [{"id": "admin-guide", "title_intent": ""}]}
        )


def test_documentation_section_rejects_blank_page_id():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {
                "sections": [
                    {
                        "id": "admin-guide",
                        "title_intent": "Administrator Guide",
                        "pages": ["admin/channel-management", "   "],
                    }
                ]
            }
        )


def test_documentation_relation_rejects_blank_source():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {"relations": [{"from": " ", "to": "b", "type": "related"}]}
        )


def test_documentation_relation_rejects_blank_target():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {"relations": [{"from": "a", "to": "", "type": "related"}]}
        )


def test_documentation_plan_rejects_duplicate_section_ids():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {
                "sections": [
                    {"id": "admin-guide", "title_intent": "Guide"},
                    {"id": "admin-guide", "title_intent": "Another guide"},
                ]
            }
        )


def test_documentation_plan_rejects_duplicate_page_ids_across_sections():
    """A page referenced in two sections is a duplicate structural reference."""
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {
                "sections": [
                    {
                        "id": "admin-guide",
                        "title_intent": "Guide",
                        "pages": ["channel-management"],
                    },
                    {
                        "id": "security-guide",
                        "title_intent": "Security",
                        "pages": ["channel-management"],
                    },
                ]
            }
        )


def test_documentation_plan_rejects_duplicate_plan_pages():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate({"pages": ["a", "a"]})


def test_documentation_plan_rejects_duplicate_pages_within_one_section():
    with pytest.raises(ValidationError):
        DocumentationPlan.model_validate(
            {
                "sections": [
                    {
                        "id": "admin-guide",
                        "title_intent": "Guide",
                        "pages": ["channel-management", "channel-management"],
                    }
                ]
            }
        )


def test_documentation_plan_permits_shared_page_across_plan_and_one_section():
    """A page listed both at plan level and in a single section is not duplicated.

    The plan-level ``pages`` is an index of all planned pages, so the same page
    legitimately appears in one section; only an actual repeated reference (two
    sections, or two plan entries) is a structural error.
    """
    plan = DocumentationPlan(
        pages=["channel-management"],
        sections=[
            DocumentationSection(
                id="admin-guide",
                title_intent="Administrator Guide",
                pages=["channel-management"],
            )
        ],
    )
    assert plan.pages == ["channel-management"]
    assert plan.sections[0].pages == ["channel-management"]


# --- V3-P3-03: plan <-> PageSpec structural consistency (mechanical only) ---


def _spec(page_id: str) -> PageSpec:
    return PageSpec(
        page_id=page_id,
        page_type="concept",
        title_intent="T",
        user_goal="G",
        audience=["admin"],
        required_sections=["overview"],
    )


def test_plan_page_consistency_empty_when_consistent():
    plan = DocumentationPlan(
        pages=["a"],
        sections=[
            DocumentationSection(id="s1", title_intent="S1", pages=["a", "b"])
        ],
        relations=[
            DocumentationRelation(from_="a", to="b", type="related"),
        ],
    )
    specs = [_spec("a"), _spec("b")]
    assert plan_page_consistency_errors(plan, specs) == []


def test_plan_page_consistency_flags_missing_pagespec():
    plan = DocumentationPlan(
        pages=["a", "ghost"],
        sections=[DocumentationSection(id="s1", title_intent="S1", pages=["a"])],
    )
    specs = [_spec("a")]
    errors = plan_page_consistency_errors(plan, specs)
    assert len(errors) == 1
    assert "ghost" in errors[0]
    assert "no matching PageSpec" in errors[0]


def test_plan_page_consistency_flags_relation_to_missing_page():
    plan = DocumentationPlan(
        pages=["a"],
        relations=[
            DocumentationRelation(from_="a", to="ghost", type="related"),
        ],
    )
    specs = [_spec("a")]
    errors = plan_page_consistency_errors(plan, specs)
    assert len(errors) == 1
    assert "ghost" in errors[0]


def test_plan_page_consistency_flags_duplicate_pagespec_ids():
    plan = DocumentationPlan(pages=["a"])
    specs = [_spec("a"), _spec("a")]
    errors = plan_page_consistency_errors(plan, specs)
    assert len(errors) == 1
    assert "Duplicate PageSpec.page_id" in errors[0]


def test_plan_page_consistency_does_not_judge_section_placement():
    """The check never complains that a page sits in the 'wrong' section: any
    page that has a PageSpec is consistent, wherever the Architect placed it."""
    plan = DocumentationPlan(
        sections=[
            DocumentationSection(id="s1", title_intent="S1", pages=["a"]),
            DocumentationSection(id="s2", title_intent="S2", pages=["b"]),
        ]
    )
    specs = [_spec("a"), _spec("b")]
    assert plan_page_consistency_errors(plan, specs) == []
