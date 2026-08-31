"""Tests for V3 cognitive handoff artifact models.

These artifacts are LLM-authored; Python only validates the schema and
serializes. Tests confirm validation strictness (``extra="forbid"``) and a
serialization round-trip — never that Python infers semantic content.
"""

from makewiki_skills.model.v3_artifacts import (
    ExistingDocumentation,
    HighInformationSource,
    LikelyUser,
    MajorArea,
    RepositoryBrief,
    RepositoryHypothesis,
)

import pytest
from pydantic import ValidationError


def _sample_brief() -> RepositoryBrief:
    return RepositoryBrief(
        project_hypothesis=RepositoryHypothesis(
            name="acme-cli",
            purpose="Manage upstream provider channels and routing.",
            type="CLI tool",
            confidence="medium",
        ),
        likely_users=[
            LikelyUser(persona_hint="operator", reason="Manages providers."),
            LikelyUser(persona_hint="admin", reason="Configures channels."),
        ],
        major_areas=[
            MajorArea(
                id="channel-management",
                meaning_hypothesis="Provider channel configuration surface.",
                likely_paths=["src/channels/"],
                confidence="medium",
            )
        ],
        high_information_sources=[
            HighInformationSource(path="README.md", reason="Usage overview.")
        ],
        existing_documentation=[
            ExistingDocumentation(
                path_or_url="docs/", standing="possibly_stale"
            )
        ],
        important_unknowns=["Exact auth model for the admin API."],
        orientation_notes=["Confidence is provisional pending investigation."],
    )


def test_repository_brief_serialization_round_trip():
    brief = _sample_brief()
    payload = brief.model_dump_json()
    rebuilt = RepositoryBrief.model_validate_json(payload)
    assert rebuilt == brief


def test_repository_brief_defaults_are_empty():
    """An empty handoff serializes to empty lists / unknowns, never guessed."""
    brief = RepositoryBrief()
    payload = brief.model_dump_json()
    rebuilt = RepositoryBrief.model_validate_json(payload)
    assert rebuilt == brief
    assert rebuilt.project_hypothesis.name == ""
    assert rebuilt.project_hypothesis.confidence == "medium"
    assert rebuilt.likely_users == []
    assert rebuilt.important_unknowns == []


def test_repository_brief_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        RepositoryBrief.model_validate({"not_a_field": "boom"})


def test_repository_brief_rejects_unknown_nested_keys():
    with pytest.raises(ValidationError):
        RepositoryBrief.model_validate(
            {"project_hypothesis": {"fabricated": True}}
        )
