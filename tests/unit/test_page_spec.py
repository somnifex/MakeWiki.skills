"""Tests for LLM-authored PageSpec validation model.

The PageSpec is the Writer's contract. Python only validates the schema, checks
``page_type`` against the allowed vocabulary, and serializes — it never splits
pages or infers a page type.
"""

import pytest
from pydantic import ValidationError

from makewiki_skills.model.page_spec import PageSpec, PageType


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


def test_page_spec_rejects_blank_audience_entries():
    """audience must not contain blank strings (a non-empty list of empty entries
    would otherwise bypass the top-level non-empty check)."""
    base = {
        "page_id": "admin/channel-management",
        "page_type": "feature_guide",
        "title_intent": "Channel Management",
        "user_goal": "Configure upstream channels.",
        "required_sections": ["overview"],
    }
    for audience in ([""], ["admin", "  "], ["   "]):
        with pytest.raises(ValidationError):
            PageSpec.model_validate({**base, "audience": audience})


def test_page_spec_rejects_blank_required_section_entries():
    """required_sections must not contain blank strings (same loophole)."""
    base = {
        "page_id": "admin/channel-management",
        "page_type": "feature_guide",
        "title_intent": "Channel Management",
        "user_goal": "Configure upstream channels.",
        "audience": ["admin"],
    }
    for sections in ([""], ["overview", "  "], ["   "]):
        with pytest.raises(ValidationError):
            PageSpec.model_validate({**base, "required_sections": sections})


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


def test_page_spec_language_is_optional_legacy():
    """A PageSpec is a language-neutral semantic writing contract: ``language`` is a
    compatibility / legacy field that is optional and NOT authoritative for V3
    target-language selection. A valid spec may carry no language at all, and one
    canonical PageSpec serves every target language's draft."""
    spec = PageSpec(
        page_id="admin/channel-management",
        page_type="feature_guide",
        title_intent="Channel Management",
        user_goal="Configure upstream channels.",
        audience=["admin"],
        required_sections=["overview"],
        # language intentionally omitted -> defaults to "" (no required language)
    )
    assert spec.language == ""
    payload = spec.model_dump_json()
    rebuilt = PageSpec.model_validate_json(payload)
    assert rebuilt == spec
    assert rebuilt.language == ""


def test_page_spec_language_value_does_not_change_canonical_identity():
    """Loading the same PageSpec with different ``language`` values does not change
    the language-neutral identity (page_id/covers/required_sections stay fixed)."""
    base = {
        "page_id": "admin/channel-management",
        "page_type": "feature_guide",
        "title_intent": "Channel Management",
        "user_goal": "Configure upstream channels.",
        "audience": ["admin"],
        "required_sections": ["overview"],
    }
    zh = PageSpec.model_validate({**base, "language": "zh-CN"})
    en = PageSpec.model_validate({**base, "language": "en"})
    none = PageSpec.model_validate(base)
    assert zh.page_id == en.page_id == none.page_id == "admin/channel-management"
    assert zh.covers == en.covers == none.covers
    assert zh.required_sections == en.required_sections == none.required_sections
