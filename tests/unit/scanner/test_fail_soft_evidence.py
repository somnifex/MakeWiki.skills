"""Unit tests for Fail-Soft Evidence collection and YAML safe normalization."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.evidence_collector import EvidenceCollector, _pruned_walk
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType
from makewiki_skills.toolkit.config_reader import ConfigReaderTool
from makewiki_skills.toolkit.evidence import EvidenceTool


def test_pruned_walk_skips_ignored_directories_entirely(tmp_path: Path):
    """Ignored directories like node_modules/.git are not traversed."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")

    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "foo.js").write_text("module.exports = {};\n", encoding="utf-8")

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")

    walked = _pruned_walk(tmp_path, ignore_dirs={"node_modules", ".git"}, max_depth=5)
    rel_paths = [rel for _, rel in walked]

    assert "src/index.ts" in rel_paths
    assert not any("node_modules" in r for r in rel_paths)
    assert not any(".git" in r for r in rel_paths)


def test_extractor_exception_isolation_records_tool_error(tmp_path: Path):
    """If an extractor raises an unhandled exception, the collection pass does not crash.

    The error is logged to ToolFailureRecord, tool_health is marked TOOL_ERROR,
    and remaining extractors still succeed.
    """
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / "main.py").write_text("def run(): pass\n", encoding="utf-8")
    (proj / "config.yaml").write_text("key: value\n", encoding="utf-8")

    cfg = MakeWikiConfig.default(proj)
    collector = EvidenceCollector(cfg)

    # Mock an extractor to simulate a crash
    faulty_extractor = MagicMock()
    faulty_extractor.name = "faulty_cli_extractor"
    faulty_extractor.extract_from_file.side_effect = RuntimeError("Simulated AST crash on Python 3.14 syntax")

    collector._cli_help_extractor = faulty_extractor  # type: ignore[assignment]

    detection = ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        project_name="test_proj",
        project_dir=str(proj),
    )

    collected = collector.collect(proj, detection)

    # Collection succeeded and returned facts
    assert len(collected.facts) > 0
    # Faulty extractor logged in tool_failures
    assert any(f.extractor == "faulty_cli_extractor" for f in collected.coverage.tool_failures)
    assert collected.coverage.tool_health["faulty_cli_extractor"] == "TOOL_ERROR"


def test_github_workflows_excluded_from_app_configs(tmp_path: Path):
    """GitHub actions workflows (.github/workflows/*.yml) do not pollute app configs."""
    proj = tmp_path / "project"
    proj.mkdir()
    gh_dir = proj / ".github" / "workflows"
    gh_dir.mkdir(parents=True)
    (gh_dir / "ci.yml").write_text("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8")

    (proj / "app_config.yaml").write_text("app:\n  port: 8080\n", encoding="utf-8")

    cfg = MakeWikiConfig.default(proj)
    collector = EvidenceCollector(cfg)
    detection = ProjectDetectionResult(
        project_type=ProjectType.GENERIC,
        project_name="test_proj",
        project_dir=str(proj),
    )

    collected = collector.collect(proj, detection)
    config_claims = [f.value for f in collected.facts if f.fact_type == "config_key"]

    assert "app.port" in config_claims
    # CI runners parameters are NOT extracted as app config keys
    assert not any("ubuntu-latest" in str(f.claim) for f in collected.facts)
    assert not any("jobs.test" in str(c) for c in config_claims)


def test_yaml_safe_normalization_and_defensive_types(tmp_path: Path):
    """YAML booleans, nulls, lists, and numbers parse safely without crashing."""
    yaml_file = tmp_path / "settings.yaml"
    yaml_file.write_text(
        """
        enabled: yes
        disabled: no
        active: true
        inactive: false
        power: on
        sleep: off
        empty_val: null
        tilde_val: ~
        port: 8080
        ratio: 3.14
        items:
          - name: a
            val: 1
          - name: b
            val: 2
        scalar_list:
          - foo
          - bar
        """,
        encoding="utf-8",
    )

    reader = ConfigReaderTool()
    res = reader.read_yaml(yaml_file)
    assert res.success
    data = res.data

    assert data["enabled"] is True
    assert data["disabled"] is False
    assert data["active"] is True
    assert data["inactive"] is False
    assert data["power"] is True
    assert data["sleep"] is False
    assert data["empty_val"] is None
    assert data["tilde_val"] is None
    assert data["port"] == 8080
    assert data["ratio"] == 3.14

    paths = reader.extract_key_paths(data)
    assert "enabled" in paths
    assert "items[0].name" in paths

    # Test extract_config_keys on safely normalized data
    evidence_tool = EvidenceTool()
    facts = evidence_tool.extract_config_keys(data, "settings.yaml")
    assert len(facts) > 0


def test_coverage_split_counts_tracking(tmp_path: Path):
    """CoverageReport properly populates split counts."""
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / "pyproject.toml").write_text('[project]\nname="app"\nversion="0.1.0"\n', encoding="utf-8")
    (proj / "config.yaml").write_text("db:\n  host: localhost\n", encoding="utf-8")
    (proj / "README.md").write_text("# App\n\nRun command:\n```bash\napp start\n```\n", encoding="utf-8")

    tests_dir = proj / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_app(): pass\n", encoding="utf-8")

    cfg = MakeWikiConfig.default(proj)
    collector = EvidenceCollector(cfg)
    detection = ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        project_name="app",
        project_dir=str(proj),
    )

    collected = collector.collect(proj, detection)
    cov = collected.coverage

    assert cov.files_discovered >= 4
    assert cov.files_read >= 2
    assert cov.files_parsed >= 2
    assert cov.files_with_facts >= 2
    assert cov.manifests_discovered == 1
    assert cov.configs_discovered == 1
    assert cov.tests_discovered == 1
