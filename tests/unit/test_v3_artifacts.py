"""Tests for V3 cognitive handoff artifact models.

These artifacts are LLM-authored; Python only validates the schema and
serializes. Tests confirm validation strictness (``extra="forbid"``) and a
serialization round-trip — never that Python infers semantic content.
"""

from makewiki_skills.model.v3_artifacts import (
    Claim,
    ClaimBundle,
    ClaimEvidence,
    ExistingDocumentation,
    HighInformationSource,
    InvestigationPlan,
    InvestigationPlanDomain,
    LikelyUser,
    MajorArea,
    RepositoryBrief,
    RepositoryHypothesis,
    ReviewFinding,
    ReviewFindings,
    ScopeExpansion,
    SubtaskOutputSpec,
    SubtaskSpec,
    SubtaskType,
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


def _sample_subtask() -> SubtaskSpec:
    return SubtaskSpec(
        id="investigate.management-api",
        type="investigation",
        goal="Understand the management API as an operator/admin interface.",
        context="Channel routing depends on the management API.",
        scope_hint=["management handlers", "request/response models"],
        questions=["What operations are exposed?", "Who may call them?"],
        inputs=["repository_brief", "relevant prior claims"],
        expected_output=SubtaskOutputSpec(
            type="ClaimBundle", id="claims.management-api"
        ),
        depends_on=["orientation.global"],
        stop_conditions=[
            "major management operations identified",
            "every important claim has evidence",
        ],
    )


def test_subtask_spec_serialization_round_trip():
    subtask = _sample_subtask()
    payload = subtask.model_dump_json()
    rebuilt = SubtaskSpec.model_validate_json(payload)
    assert rebuilt == subtask


def test_subtask_spec_defaults_are_empty():
    subtask = SubtaskSpec()
    payload = subtask.model_dump_json()
    rebuilt = SubtaskSpec.model_validate_json(payload)
    assert rebuilt == subtask
    assert rebuilt.id == ""
    assert rebuilt.scope_hint == []
    assert rebuilt.depends_on == []


def test_subtask_spec_validates_type_vocabulary():
    with pytest.raises(ValidationError):
        SubtaskSpec.model_validate({"type": "everything"})


def test_subtask_type_accepts_all_contract_values():
    for value in SubtaskType.__args__:
        assert SubtaskSpec.model_validate({"type": value}).type == value


def test_subtask_spec_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        SubtaskSpec.model_validate({"scheduler": "run_everything"})


def _sample_investigation_plan() -> InvestigationPlan:
    return InvestigationPlan(
        project_hypothesis="A channel routing CLI for operator use.",
        domains=[
            InvestigationPlanDomain(
                id="channel-management",
                why_important="Core operator surface.",
                goal="Understand channel configuration.",
                scope_hint=["src/channels/"],
                related_domains=["routing"],
            )
        ],
        subtasks=[
            SubtaskSpec(
                id="investigate.channel-management",
                type="investigation",
                goal="Understand channel configuration.",
                questions=["What operations are exposed?"],
                expected_output=SubtaskOutputSpec(
                    type="ClaimBundle", id="claims.channel-management"
                ),
            )
        ],
        coverage_questions=["Can every domain be grounded?"],
        known_uncertainties=["Auth model for the admin API."],
    )


def test_investigation_plan_serialization_round_trip():
    plan = _sample_investigation_plan()
    payload = plan.model_dump_json()
    rebuilt = InvestigationPlan.model_validate_json(payload)
    assert rebuilt == plan


def test_investigation_plan_defaults_are_empty():
    plan = InvestigationPlan()
    payload = plan.model_dump_json()
    rebuilt = InvestigationPlan.model_validate_json(payload)
    assert rebuilt == plan
    assert rebuilt.domains == []
    assert rebuilt.subtasks == []
    assert rebuilt.known_uncertainties == []


def test_investigation_plan_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        InvestigationPlan.model_validate({"pick_next_domain": True})


def _sample_claim_bundle() -> ClaimBundle:
    return ClaimBundle(
        id="claims.channel-management",
        domain="channel-management",
        producer_subtask="investigate.channel-management",
        summary="Channel configuration surface.",
        claims=[
            Claim(
                id="channel.create",
                statement="Admin can create a provider channel.",
                semantic_key="channel.create",
                confidence="high",
                visibility=["admin", "operator"],
                abstraction="workflow",
                evidence=[
                    ClaimEvidence(
                        path="src/channels/create.py",
                        symbol_or_location="create_channel",
                        rationale="Handles channel creation request.",
                    )
                ],
                uncertainty=None,
            )
        ],
        unresolved=["Exact auth model."],
        newly_discovered_areas=["routing"],
        recommended_followups=["investigate.routing"],
        scope_expansions=[
            ScopeExpansion(
                path="src/routing/", reason="Discovered routing semantics."
            )
        ],
    )


def test_claim_bundle_serialization_round_trip():
    bundle = _sample_claim_bundle()
    payload = bundle.model_dump_json()
    rebuilt = ClaimBundle.model_validate_json(payload)
    assert rebuilt == bundle


def test_claim_bundle_defaults_are_empty():
    bundle = ClaimBundle()
    payload = bundle.model_dump_json()
    rebuilt = ClaimBundle.model_validate_json(payload)
    assert rebuilt == bundle
    assert rebuilt.claims == []
    assert rebuilt.unresolved == []


def test_visibility_abstraction_are_opaque_strings():
    """Python must not classify or restrict visibility/abstraction.

    The LLM writes these classifications; Python stores them verbatim and never
    imposes a vocabulary or infers them from structure.
    """
    bundle = ClaimBundle(
        claims=[
            Claim(
                id="c1",
                visibility=["public", "operator"],
                abstraction="interface",
            )
        ]
    )
    claim = bundle.claims[0]
    assert claim.visibility == ["public", "operator"]
    assert claim.abstraction == "interface"
    # A novel / unknown-classification string is stored as authored, not rejected.
    bundle2 = ClaimBundle(claims=[Claim(id="c2", abstraction="some_new_kind")])
    assert bundle2.claims[0].abstraction == "some_new_kind"


def test_claim_bundle_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ClaimBundle.model_validate({"inferred_personas": []})


def _sample_review_findings() -> ReviewFindings:
    return ReviewFindings(
        page_id="channel-management",
        language="zh-CN",
        mode="documentation_fitness",
        status="changes_required",
        findings=[
            ReviewFinding(
                id="finding-001",
                severity="major",
                category="task_incompleteness",
                location="创建渠道",
                problem="Prerequisite step omitted.",
                evidence_refs=["src/channels/create.py"],
                required_change="Add the prerequisite step.",
            )
        ],
        passed_checks=["Section IDs preserved."],
        unresolved=["Exact auth model."],
    )


def test_review_findings_serialization_round_trip():
    review = _sample_review_findings()
    payload = review.model_dump_json()
    rebuilt = ReviewFindings.model_validate_json(payload)
    assert rebuilt == review


def test_review_findings_defaults_are_empty():
    review = ReviewFindings()
    payload = review.model_dump_json()
    rebuilt = ReviewFindings.model_validate_json(payload)
    assert rebuilt == review
    assert rebuilt.findings == []
    assert rebuilt.passed_checks == []


def test_review_findings_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ReviewFindings.model_validate({"edited_page": True})
