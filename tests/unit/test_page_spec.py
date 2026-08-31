"""Tests for LLM-authored PageSpec validation model.

The PageSpec is the Writer's contract. Python only validates the schema, checks
``page_type`` against the allowed vocabulary, and serializes — it never splits
pages or infers a page type.
"""

from makewiki_skills.model.page_spec import PageSpec, PageType

import pytest
from pydantic import ValidationError


def _sample_spec() -> PageSpec:
    return PageSpec(
        page_id="admin/channel-management",
        page_type="feature_guide",
        title_intent="Channel Management",
        audience=["admin", "operator"],
        user_goal="Configure and validate upstream provider channels.",
        covers=["channel.create", "channel.edit", "channel.test"],
        required_sections=[
            "overview",
            "prerequisites",
            "create",
            "configuration-fields",
            "related",
        ],
        required_facts=[],
        optional_facts=[],
        forbidden_topics=["ORM implementation details"],
        source_claims=[],
        semantic_refs=[],
        documentation_refs=[],
        related_pages=["admin/channel-routing", "reference/management-api/channels"],
        language="zh-CN",
    )


def test_page_spec_serialization_round_trip():
    spec = _sample_spec()
    payload = spec.model_dump_json()
    rebuilt = PageSpec.model_validate_json(payload)
    assert rebuilt == spec
    assert rebuilt.page_id == "admin/channel-management"
    assert rebuilt.page_type == "feature_guide"
    assert rebuilt.language == "zh-CN"


def test_page_spec_rejects_empty_shell():
    """An empty PageSpec is no page at all and must be rejected.

    A Writer must be handed a concrete page: non-blank ``page_id`` /
    ``title_intent`` / ``user_goal`` plus at least one ``audience`` and one
    ``required_section``.
    """
    with pytest.raises(ValidationError):
        PageSpec()


def test_page_spec_rejects_blank_page_id():
    with pytest.raises(ValidationError):
        PageSpec(
            page_id="  ",
            page_type="feature_guide",
            title_intent="Channel Management",
            user_goal="Configure upstream channels.",
            audience=["admin"],
            required_sections=["overview"],
        )


def test_page_spec_rejects_empty_audience():
    with pytest.raises(ValidationError):
        PageSpec(
            page_id="admin/channel-management",
            page_type="feature_guide",
            title_intent="Channel Management",
            user_goal="Configure upstream channels.",
            audience=[],
            required_sections=["overview"],
        )


def test_page_spec_rejects_empty_required_sections():
    with pytest.raises(ValidationError):
        PageSpec(
            page_id="admin/channel-management",
            page_type="feature_guide",
            title_intent="Channel Management",
            user_goal="Configure upstream channels.",
            audience=["admin"],
            required_sections=[],
        )


def test_page_spec_allows_empty_optional_facts_and_related_pages():
    """``optional_facts`` / ``forbidden_topics`` / ``related_pages`` may be empty."""
    spec = _sample_spec()
    assert spec.optional_facts == []
    assert spec.forbidden_topics == ["ORM implementation details"]


def test_page_type_validates_allowed_vocabulary():
    with pytest.raises(ValidationError):
        PageSpec.model_validate({"page_type": "fabricated_type"})


def test_page_type_accepts_all_contract_values():
    base = {
        "page_id": "p",
        "title_intent": "T",
        "user_goal": "G",
        "audience": ["admin"],
        "required_sections": ["overview"],
    }
    for value in PageType.__args__:
        assert PageSpec.model_validate({**base, "page_type": value}).page_type == value


def test_page_spec_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        PageSpec.model_validate({"auto_split": True})
