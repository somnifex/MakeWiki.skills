"""Tests for ProjectDetector."""

from pathlib import Path

from makewiki_skills.scanner.project_detector import ProjectDetector, ProjectType


def test_detect_python_cli(minimal_python_cli_dir: Path):
    detector = ProjectDetector()
    result = detector.detect(minimal_python_cli_dir)
    assert result.project_type == ProjectType.PYTHON_CLI
    assert result.confidence > 0
    assert "pyproject.toml" in result.indicators_found
    assert result.project_name == "mini-cli"


def test_detect_node_app(minimal_node_app_dir: Path):
    detector = ProjectDetector()
    result = detector.detect(minimal_node_app_dir)
    assert result.project_type in (ProjectType.NODE_CLI, ProjectType.NODE_LIBRARY)
    assert result.project_name == "mini-node-app"


def test_detect_generic(tmp_path: Path):
    (tmp_path / "random.txt").write_text("hello")
    detector = ProjectDetector()
    result = detector.detect(tmp_path)
    assert result.project_type == ProjectType.GENERIC
    assert result.confidence == 0.3


def test_detect_node_react(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "react-app"}')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "App.tsx").write_text("export default function App() {}")
    detector = ProjectDetector()
    result = detector.detect(tmp_path)
    assert result.project_type == ProjectType.NODE_REACT


def test_detect_rust_cli(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "mycli"\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}")
    detector = ProjectDetector()
    result = detector.detect(tmp_path)
    assert result.project_type == ProjectType.RUST_CLI
