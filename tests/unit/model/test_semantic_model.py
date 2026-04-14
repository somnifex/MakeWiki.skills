"""Tests for SemanticModel."""

from makewiki_skills.model.semantic_model import (
    Command,
    ConfigItem,
    ConfigSection,
    InstallStep,
    InstallationGuide,
    ProjectIdentity,
    SemanticModel,
)
from makewiki_skills.scanner.project_detector import ProjectType


def test_semantic_model_creation():
    model = SemanticModel(
        identity=ProjectIdentity(name="test-project", version="1.0.0"),
        project_type=ProjectType.PYTHON_CLI,
    )
    assert model.identity.name == "test-project"
    assert model.project_type == ProjectType.PYTHON_CLI


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


def test_installation_guide():
    guide = InstallationGuide(
        steps=[
            InstallStep(order=1, title="Clone", commands=["git clone repo"]),
            InstallStep(order=2, title="Install", commands=["pip install -e ."]),
        ],
        verify_command="test --version",
    )
    assert len(guide.steps) == 2
    assert guide.verify_command == "test --version"
