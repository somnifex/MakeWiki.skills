"""Tests for SemanticModel."""

from makewiki_skills.model.rebattle import (
    AdjudicatedClaim,
    AdjudicationResult,
    AgentClaim,
    fold_adjudicated_into_semantic_model,
)
from makewiki_skills.model.semantic_model import (
    Command,
    ConfigItem,
    ConfigSection,
    ProjectIdentity,
    SemanticModel,
)


def test_semantic_model_to_context_dict():
    model = SemanticModel(
        identity=ProjectIdentity(name="test", description="A test project"),
        commands=[
            Command(name="test serve", description="Start server"),
            Command(name="test build", description="Build project"),
        ],
        configuration=[
            ConfigSection(
                name="Server",
                items=[ConfigItem(key="port", default_value="8080")],
            )
        ],
    )
    ctx = model.to_context_dict()
    assert ctx["identity"]["name"] == "test"
    assert len(ctx["commands"]) == 2
    assert len(ctx["configuration"]) == 1


def test_authoritative_semantic_model_not_generated_by_task_inference():
    """Python never invents cognitive fields without a Judge ruling.

    Feeding only raw AgentClaims (no adjudication) must leave the model's
    cognitive fields EMPTY / unknown. Only after AdjudicatedClaims (an explicit
    Judge ruling) are supplied do those fields populate — and fold marks their
    provenance as LLM-authored, never python.
    """
    model = SemanticModel()

    workflow = AgentClaim(
        agent_id="agent_red",
        perspective="user_experience",
        claim_type="workflow",
        semantic_key="workflow.auth",
        assertion="Login -> token -> refresh flow.",
    )
    faq = AgentClaim(
        agent_id="agent_blue",
        perspective="code_implementation",
        claim_type="faq_topic",
        semantic_key="faq.install",
        assertion="Running `make setup` installs dependencies.",
    )

    # No Judge ruling -> no cognitive content, provenance stays "unknown".
    only_agent_claims = fold_adjudicated_into_semantic_model([], model)
    assert only_agent_claims.user_tasks == []
    assert only_agent_claims.faq == []
    assert only_agent_claims.troubleshooting == []
    assert only_agent_claims.provenance.user_tasks == "unknown"
    assert only_agent_claims.provenance.faq == "unknown"

    # A Judge ruling converts those AgentClaims into AdjudicatedClaims, which
    # are then the ONLY thing allowed into the authoritative model.
    adjudications = [
        AdjudicationResult(
            discrepancy_topic="workflow.auth",
            ruling="accepted",
            final_assertion="Login -> token -> refresh, then JWT issued.",
            adjudicator_reasoning="Verified against auth module.",
        ),
        AdjudicationResult(
            discrepancy_topic="faq.install",
            ruling="accepted",
            final_assertion="`make setup` installs all dependencies.",
            adjudicator_reasoning="Verified against Makefile.",
        ),
    ]
    adjudicated = [
        AdjudicatedClaim(
            claim=workflow,
            ruling=adjudications[0].ruling,
            final_assertion=adjudications[0].final_assertion,
            adjudicator_reasoning=adjudications[0].adjudicator_reasoning,
        ),
        AdjudicatedClaim(
            claim=faq,
            ruling=adjudications[1].ruling,
            final_assertion=adjudications[1].final_assertion,
            adjudicator_reasoning=adjudications[1].adjudicator_reasoning,
        ),
    ]

    populated = fold_adjudicated_into_semantic_model(adjudicated, model)
    assert len(populated.user_tasks) == 1
    assert populated.user_tasks[0].title == "workflow.auth"
    assert len(populated.faq) == 1
    assert "make setup" in populated.faq[0].answer
    assert populated.provenance.user_tasks == "llm"
    assert populated.provenance.faq == "llm"
