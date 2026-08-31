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


def test_repository_brief_rejects_empty_shell():
    """An Orientation that outputs nothing to investigate is not a valid Brief.

    ``major_areas`` may be empty, but then at least one ``important_unknown``
    must be present; ``project_hypothesis`` key prose must be non-blank.
    """
    with pytest.raises(ValidationError):
        RepositoryBrief()


def test_repository_brief_requires_project_hypothesis_text():
    """The hypothesis's ``name`` / ``purpose`` must not be blank."""
    with pytest.raises(ValidationError):
        RepositoryBrief(
            project_hypothesis=RepositoryHypothesis(
                name="", purpose="  ", type="CLI tool"
            ),
            major_areas=[
                MajorArea(id="x", meaning_hypothesis="A domain.")
            ],
        )


def test_repository_brief_accepts_unknowns_instead_of_areas():
    """``major_areas`` may be empty as long as an ``important_unknown`` exists."""
    brief = RepositoryBrief(
        project_hypothesis=RepositoryHypothesis(
            name="acme", purpose="route channels", type="CLI tool"
        ),
        major_areas=[],
        important_unknowns=["Exact auth model."],
    )
    assert brief.important_unknowns == ["Exact auth model."]


def test_repository_brief_rejects_empty_high_information_source():
    """A flagged high-information source must carry both ``path`` and ``reason``."""
    with pytest.raises(ValidationError):
        RepositoryBrief(
            project_hypothesis=RepositoryHypothesis(
                name="acme", purpose="route channels", type="CLI tool"
            ),
            high_information_sources=[
                HighInformationSource(path="README.md", reason="  ")
            ],
            major_areas=[
                MajorArea(id="x", meaning_hypothesis="A domain.")
            ],
        )


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


def test_subtask_spec_defaults_are_rejected():
    """An empty SubtaskSpec describes no executable work and must be rejected.

    It must carry a non-blank ``id`` / ``goal``, a fully-specified
    ``expected_output``, and at least one ``stop_condition``.
    """
    with pytest.raises(ValidationError):
        SubtaskSpec()


def test_subtask_spec_rejects_blank_id():
    with pytest.raises(ValidationError):
        SubtaskSpec(
            id="  ",
            goal="Understand the management API.",
            expected_output=SubtaskOutputSpec(
                type="ClaimBundle", id="claims.management-api"
            ),
            stop_conditions=["Major operations identified."],
        )


def test_subtask_spec_rejects_empty_goal():
    with pytest.raises(ValidationError):
        SubtaskSpec(
            id="investigate.management-api",
            goal="",
            expected_output=SubtaskOutputSpec(
                type="ClaimBundle", id="claims.management-api"
            ),
            stop_conditions=["Major operations identified."],
        )


def test_subtask_spec_rejects_incomplete_expected_output():
    """``expected_output.type`` and ``expected_output.id`` must both be set."""
    with pytest.raises(ValidationError):
        SubtaskSpec(
            id="investigate.management-api",
            goal="Understand the management API.",
            expected_output=SubtaskOutputSpec(type="", id=""),
            stop_conditions=["Major operations identified."],
        )


def test_subtask_spec_rejects_empty_stop_conditions():
    """A subtask must declare at least one stop_condition (no unbounded runs)."""
    with pytest.raises(ValidationError):
        SubtaskSpec(
            id="investigate.management-api",
            goal="Understand the management API.",
            expected_output=SubtaskOutputSpec(
                type="ClaimBundle", id="claims.management-api"
            ),
            stop_conditions=[],
        )


def test_subtask_spec_validates_type_vocabulary():
    with pytest.raises(ValidationError):
        SubtaskSpec.model_validate({"type": "everything"})


def test_subtask_type_accepts_all_contract_values():
    base = {
        "id": "subtask.placeholder",
        "goal": "Placeholder goal.",
        "expected_output": {"type": "ClaimBundle", "id": "claims.placeholder"},
        "stop_conditions": ["Placeholder stop condition."],
    }
    for value in SubtaskType.__args__:
        assert SubtaskSpec.model_validate({**base, "type": value}).type == value


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
                stop_conditions=["Every important claim has evidence."],
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
                statement="Admin can create a provider channel.",
                semantic_key="channel.create",
                visibility=["public", "operator"],
                abstraction="interface",
                evidence=[
                    ClaimEvidence(path="src/", rationale="Source inspection.")
                ],
            )
        ]
    )
    claim = bundle.claims[0]
    assert claim.visibility == ["public", "operator"]
    assert claim.abstraction == "interface"
    # A novel / unknown-classification string is stored as authored, not rejected.
    bundle2 = ClaimBundle(
        claims=[
            Claim(
                id="c2",
                statement="A provisionally grounded claim.",
                semantic_key="provisional",
                abstraction="some_new_kind",
                uncertainty="Not yet fully confirmed.",
            )
        ]
    )
    assert bundle2.claims[0].abstraction == "some_new_kind"


def test_claim_bundle_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ClaimBundle.model_validate({"inferred_personas": []})


def test_claim_rejects_empty_shell():
    """A claim must carry non-blank id / statement / semantic_key."""
    with pytest.raises(ValidationError):
        ClaimBundle(
            claims=[
                Claim(
                    id="",
                    statement="",
                    semantic_key="",
                    evidence=[
                        ClaimEvidence(path="src/", rationale="Source inspection.")
                    ],
                )
            ]
        )


def test_claim_rejects_no_evidence_and_no_uncertainty():
    """``evidence=[]`` with ``uncertainty=None`` is forbidden: an ungrounded,
    un-hedged assertion must not pass as valid canonical output."""
    with pytest.raises(ValidationError):
        ClaimBundle(
            claims=[
                Claim(
                    id="channel.create",
                    statement="Admin can create a provider channel.",
                    semantic_key="channel.create",
                )
            ]
        )


def test_claim_accepts_explicit_uncertainty_without_evidence():
    """An un-evidenced claim is tolerable only when it carries explicit uncertainty."""
    claim = Claim(
        id="auth.model",
        statement="Exact auth model is not yet confirmed.",
        semantic_key="auth.model",
        uncertainty="Disputed across sources; needs follow-up.",
    )
    assert claim.uncertainty is not None


def test_claim_rejects_empty_evidence_item():
    """Each evidence item must carry both ``path`` and ``rationale``."""
    with pytest.raises(ValidationError):
        ClaimBundle(
            claims=[
                Claim(
                    id="channel.create",
                    statement="Admin can create a provider channel.",
                    semantic_key="channel.create",
                    evidence=[
                        ClaimEvidence(path="src/", rationale="  ")
                    ],
                )
            ]
        )


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
