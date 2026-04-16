"""Tests for EvidenceCollector."""

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.evidence_collector import EvidenceCollector
from makewiki_skills.scanner.project_detector import ProjectDetector, ProjectDetectionResult, ProjectType


def test_collect_python_cli(minimal_python_cli_dir: Path):
    detector = ProjectDetector()
    detection = detector.detect(minimal_python_cli_dir)

    config = MakeWikiConfig.default(minimal_python_cli_dir)
    collector = EvidenceCollector(config)
    evidence = collector.collect(minimal_python_cli_dir, detection)

    assert len(evidence.facts) > 0
    fact_types = {f.fact_type for f in evidence.facts}
    assert "path" in fact_types  # directory structure
    assert "command" in fact_types  # from pyproject scripts and/or README


def test_collect_node_app(minimal_node_app_dir: Path):
    detector = ProjectDetector()
    detection = detector.detect(minimal_node_app_dir)

    config = MakeWikiConfig.default(minimal_node_app_dir)
    collector = EvidenceCollector(config)
    evidence = collector.collect(minimal_node_app_dir, detection)

    assert len(evidence.facts) > 0
    # Should find scripts from package.json
    cmd_facts = [f for f in evidence.facts if f.fact_type == "command"]
    assert len(cmd_facts) > 0


def test_collect_extracts_description(sample_python_cli_dir: Path):
    detector = ProjectDetector()
    detection = detector.detect(sample_python_cli_dir)

    config = MakeWikiConfig.default(sample_python_cli_dir)
    collector = EvidenceCollector(config)
    evidence = collector.collect(sample_python_cli_dir, detection)

    desc_facts = [f for f in evidence.facts if f.fact_type == "description"]
    assert len(desc_facts) > 0


def test_max_depth_limits_source_intelligence(tmp_path: Path):
    """scan.max_depth should prevent scanning files nested beyond the limit."""
    # Build a project with Python files at various depths
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "depth-test"\n[project.scripts]\nmycli = "app:main"\n',
        encoding="utf-8",
    )
    # Depth 1: app.py  (parts=1, within max_depth=2)
    (tmp_path / "app.py").write_text("import typer\napp = typer.Typer()\n", encoding="utf-8")
    # Depth 2: src/core.py  (parts=2, within max_depth=2)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core.py").write_text("# core module\n", encoding="utf-8")
    # Depth 3: src/deep/nested.py  (parts=3, exceeds max_depth=2)
    (tmp_path / "src" / "deep").mkdir()
    (tmp_path / "src" / "deep" / "nested.py").write_text(
        "import typer\napp = typer.Typer(help='deeply nested')\n",
        encoding="utf-8",
    )

    config = MakeWikiConfig.default(tmp_path)
    config.scan.max_depth = 2
    config.scan.enable_source_intelligence = True

    detection = ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        project_name="depth-test",
        confidence=0.9,
    )

    collector = EvidenceCollector(config)
    evidence = collector.collect(tmp_path, detection)

    # The files read by source intelligence should NOT include the deeply nested file
    deep_files = [f for f in evidence.raw_files_read if "deep" in f]
    assert len(deep_files) == 0, f"Deeply nested files should be excluded: {deep_files}"
