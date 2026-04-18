"""Tests for SemanticModel."""

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
