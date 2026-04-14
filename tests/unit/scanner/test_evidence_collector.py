"""Tests for EvidenceCollector."""

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.evidence_collector import EvidenceCollector
from makewiki_skills.scanner.project_detector import ProjectDetector


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
