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


def test_page_spec_defaults_are_empty():
    spec = PageSpec()
    payload = spec.model_dump_json()
    rebuilt = PageSpec.model_validate_json(payload)
    assert rebuilt == spec
    assert rebuilt.audience == []
    assert rebuilt.required_sections == []
    assert rebuilt.related_pages == []


def test_page_type_validates_allowed_vocabulary():
    with pytest.raises(ValidationError):
        PageSpec.model_validate({"page_type": "fabricated_type"})


def test_page_type_accepts_all_contract_values():
    for value in PageType.__args__:
        assert PageSpec.model_validate({"page_type": value}).page_type == value


def test_page_spec_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        PageSpec.model_validate({"auto_split": True})
