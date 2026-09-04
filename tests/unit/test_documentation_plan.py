"""Tests for the LLM-authored DocumentationPlan validation model.

The DocumentationPlan is the Architect's page-structure handoff. Python only
validates the schema and serializes — it must never split pages, order
navigation, group personas, or infer pages from filenames. Tests confirm the
schema (including the ``relations[].from`` alias round-trip), strictness
(``extra="forbid"``), that a *real* plan may be minimal (no relations/rationale),
and that a *completely empty* plan must carry an explicit ``no_documentation_reason``
instead of silently passing as complete.
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
        pages=["a", "b"],
        relations=[{"from": "a", "to": "b", "type": "related"}],
    )
    assert plan.relations[0].from_ == "a"
    dumped = plan.model_dump(by_alias=True)
    assert dumped["relations"][0]["from"] == "a"
    assert "from_" not in dumped["relations"][0]


def test_documentation_plan_defaults_require_explicit_reason():
    """A completely empty plan is rejected: Python infers nothing, so it must not
    silently accept an empty plan as complete — the Architect must explain it."""
    with pytest.raises(ValidationError):
        DocumentationPlan()
    with pytest.raises(ValidationError):
        DocumentationPlan(no_documentation_reason="")


def test_documentation_plan_empty_plan_with_reason_is_valid():
    """A genuinely empty plan is allowed when the Architect states why."""
    plan = DocumentationPlan(
        no_documentation_reason="Trivial scaffold; no documented intent yet."
    )
    assert plan.sections == []
    assert plan.pages == []
    assert plan.no_documentation_reason == (
        "Trivial scaffold; no documented intent yet."
    )


def test_documentation_plan_blank_reason_is_rejected():
    with pytest.raises(ValidationError):
        DocumentationPlan(no_documentation_reason="   ")


def test_documentation_plan_normal_plan_needs_no_reason():
    """A real plan (content present) may leave no_documentation_reason empty."""
    plan = _sample_plan()
    assert plan.no_documentation_reason is None
    # A plan of only pages (no sections, no relations) is still concrete content.
    pages_only = DocumentationPlan(pages=["channel-management"])
    assert pages_only.pages == ["channel-management"]
    assert pages_only.no_documentation_reason is None


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


# --- V3-FIX-05: reverse check — every PageSpec must be a planned page ---


def test_plan_page_consistency_flags_orphan_pagespec():
    """A PageSpec the DocumentationPlan's formal page set never references is an
    orphan: Python reports it, it does not delete or re-home it."""
    plan = DocumentationPlan(pages=["a"])
    specs = [_spec("a"), _spec("orphan")]
    errors = plan_page_consistency_errors(plan, specs)
    assert len(errors) == 1
    assert "orphan" in errors[0]
    assert "not referenced by any planned page" in errors[0]


def test_plan_page_consistency_relation_alone_does_not_plan_a_pagespec():
    """A PageSpec that only appears as a relation endpoint is STILL an orphan: a
    relation links already-planned pages; it does not itself declare a page into
    the formal page set (plan.pages / section.pages)."""
    plan = DocumentationPlan(
        pages=["a"],
        relations=[DocumentationRelation(from_="a", to="ghost", type="related")],
    )
    specs = [_spec("a"), _spec("ghost")]
    errors = plan_page_consistency_errors(plan, specs)
    # "ghost" is not formally planned -> orphan PageSpec (check 4) AND it is an
    # unplanned relation endpoint (check 3); "a" is planned, so not orphaned.
    assert len(errors) == 2
    assert any("not referenced by any planned page" in e and "ghost" in e for e in errors)
    assert any("relation endpoint" in e and "ghost" in e for e in errors)


def test_plan_page_consistency_flags_relation_to_unplanned_page():
    """A relation endpoint must be a formally planned page. Pointing a relation at
    a page that exists as a PageSpec but is not in plan.pages / section.pages is a
    structural error — the relationship dangles relative to the plan's own set."""
    plan = DocumentationPlan(
        pages=["a"],
        relations=[DocumentationRelation(from_="a", to="b", type="related")],
    )
    specs = [_spec("a"), _spec("b")]
    errors = plan_page_consistency_errors(plan, specs)
    # "b" is unplanned: relation-endpoint error (3) for the relation, and it is
    # also an orphan PageSpec (4). "a" is planned.
    assert len(errors) == 2
    assert any("relation endpoint 'b'" in e for e in errors)
    assert any("not referenced by any planned page" in e and "b" in e for e in errors)


def test_plan_page_consistency_relation_ok_when_endpoints_are_planned():
    """A relation between two formally planned pages is consistent."""
    plan = DocumentationPlan(
        pages=["a", "b"],
        relations=[DocumentationRelation(from_="a", to="b", type="related")],
    )
    specs = [_spec("a"), _spec("b")]
    assert plan_page_consistency_errors(plan, specs) == []


def test_documentation_section_accepts_personas_and_rationale():
    """Producer spelling (`personas`) and section rationale load cleanly.

    A real producer wrote section-level `personas` (plural) and a rationale
    string; the canonical contract declared `persona` (singular). Both
    spellings are schema fields now; Python only validates structure.
    """
    section = DocumentationSection.model_validate(
        {
            "id": "admin-guide",
            "title_intent": "Administrator Guide",
            "personas": ["persona.admin", "persona.root"],
            "pages": ["admin/channels"],
            "rationale": "Admin surface is this project's core management area.",
        }
    )
    assert section.persona_ids == ["persona.admin", "persona.root"]
    assert section.rationale == "Admin surface is this project's core management area."


def test_documentation_section_personas_blank_entry_rejected():
    with pytest.raises(ValidationError):
        DocumentationSection.model_validate(
            {"id": "s", "title_intent": "T", "personas": ["  "], "pages": ["a"]}
        )


def test_documentation_section_blank_rationale_rejected():
    with pytest.raises(ValidationError):
        DocumentationSection(id="s", title_intent="T", pages=["a"], rationale="   ")


def test_documentation_plan_accepts_producer_metadata_fields():
    """Plan-level metadata (id/producer/languages/design_intent/...) loads."""
    plan = DocumentationPlan.model_validate(
        {
            "id": "demo.v3.documentation-plan",
            "producer": "documentation-architect (Main Agent, orchestrated)",
            "languages": ["en", "zh-CN"],
            "source_documentation_model": "demo.v3.documentation-model",
            "design_intent": "Four primary audiences; management API by resource.",
            "sections": [
                {
                    "id": "overview",
                    "title_intent": "Welcome & Platform Overview",
                    "personas": ["persona.user", "persona.admin"],
                    "pages": ["overview"],
                    "rationale": "Single orientation page for every persona.",
                }
            ],
            "relations": [],
            "rationale": ["IA matches the project emphasis."],
        }
    )
    assert plan.id == "demo.v3.documentation-plan"
    assert plan.producer == "documentation-architect (Main Agent, orchestrated)"
    assert plan.source_documentation_model == "demo.v3.documentation-model"
    assert plan.languages == ["en", "zh-CN"]
    assert plan.design_intent.startswith("Four primary audiences")
    assert plan.sections[0].personas == ["persona.user", "persona.admin"]


def test_documentation_plan_full_producer_artifact_loads():
    """A full real-world-shaped plan (all sections + metadata) loads without
    field loss: personas, rationale, notes, plan metadata, and cross-page
    relations all survive validation."""
    from pathlib import Path

    import yaml

    fixture = Path(__file__).parent / "fixtures" / "documentation_plan_full.yaml"
    raw = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    plan = DocumentationPlan.model_validate(raw["documentation_plan"])
    assert plan.sections, "sections must survive the load"
    assert any(s.personas for s in plan.sections), "personas must not be dropped"
    assert any(s.rationale for s in plan.sections), "section rationale must not be dropped"
    assert plan.producer, "producer must be preserved"
    assert plan.languages == ["en", "zh-CN"]
