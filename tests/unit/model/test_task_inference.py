"""Tests for TaskInferenceEngine."""

from makewiki_skills.model.semantic_model import Command
from makewiki_skills.model.task_inference import TaskInferenceEngine
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType


def test_infer_only_user_facing_tasks():
    engine = TaskInferenceEngine()
    commands = [
        Command(name="make test", description="Run tests"),
        Command(name="make serve", description="Start server"),
        Command(name="make build", description="Build"),
        Command(name="make lint", description="Lint"),
        Command(name="sample-cli greet World", section="Usage"),
    ]
    detection = ProjectDetectionResult(project_type=ProjectType.PYTHON_CLI, project_name="sample-cli")

    tasks = engine.infer(commands, [], detection, EvidenceRegistry())

    titles = [task.title for task in tasks]
    assert "Start the application" in titles
    assert "Run tests" not in titles
    assert "Build the project" not in titles
    assert "Run linting" not in titles
    assert len(titles) == 1


def test_no_default_install_task():
    engine = TaskInferenceEngine()
    detection = ProjectDetectionResult(project_type=ProjectType.PYTHON_CLI, project_name="test")

    tasks = engine.infer([], [], detection, EvidenceRegistry())

    assert tasks == []


def test_infer_sign_in_task():
    engine = TaskInferenceEngine()
    commands = [Command(name="webapp login", section="Usage")]
    detection = ProjectDetectionResult(project_type=ProjectType.NODE_REACT, project_name="webapp")

    tasks = engine.infer(commands, [], detection, EvidenceRegistry())

    assert len(tasks) == 1
    assert tasks[0].title == "Sign in"


def test_no_duplicate_tasks():
    engine = TaskInferenceEngine()
    commands = [
        Command(name="sample-cli serve --port 8080", section="Usage"),
        Command(name="make serve", description="Start server"),
    ]
    detection = ProjectDetectionResult(project_type=ProjectType.PYTHON_CLI, project_name="sample-cli")

    tasks = engine.infer(commands, [], detection, EvidenceRegistry())
    start_tasks = [task for task in tasks if task.title == "Start the application"]
    assert len(start_tasks) == 1
