"""Tests for the mechanical CoverageReport produced by EvidenceCollector.

The coverage report is *pure bookkeeping*: deterministic counts and lists of
what the walk discovered, inspected, skipped (with a reason), and ignored,
plus ``uncovered_categories`` / ``low_confidence_facts`` declared for the LLM
Scout layer to act on. These tests assert the accounting, never any semantic
judgment.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.evidence_collector import EvidenceCollector
from makewiki_skills.scanner.project_detector import (
    ProjectDetectionResult,
    ProjectType,
)


def _detect(project_type: ProjectType, name: str) -> ProjectDetectionResult:
    return ProjectDetectionResult(
        project_type=project_type,
        project_name=name,
        confidence=0.9,
    )


def _make_monorepo(tmp_path: Path) -> Path:
    """A small two-package monorepo with nested config + JS/TS source."""
    root = tmp_path / "monorepo"
    root.mkdir()
    (root / "README.md").write_text("# Monorepo\n", encoding="utf-8")
    (root / "Makefile").write_text("all:\n\techo hi\n", encoding="utf-8")

    pkg_a = root / "packages" / "a"
    pkg_a.mkdir(parents=True)
    (pkg_a / "pyproject.toml").write_text(
        '[project]\nname = "a"\n[project.scripts]\ncli-a = "a:main"\n',
        encoding="utf-8",
    )
    (pkg_a / "a").mkdir()
    (pkg_a / "a" / "__init__.py").write_text("def main(): pass\n", encoding="utf-8")

    pkg_b = root / "packages" / "b"
    pkg_b.mkdir(parents=True)
    (pkg_b / "package.json").write_text(
        '{"name": "b", "scripts": {"start": "node index.js"}}\n',
        encoding="utf-8",
    )
    (pkg_b / "index.js").write_text(
        "const app = {}; app.get('/ping', (req, res) => res.send('ok'));\n",
        encoding="utf-8",
    )
    (pkg_b / "index.ts").write_text(
        "export const x: number = 1;\n",
        encoding="utf-8",
    )

    # Hidden entrypoints / nested config that old root-anchored non-recursive
    # globs would have missed.
    (root / ".env").write_text("SECRET=x\n", encoding="utf-8")
    (root / "packages" / "a" / ".env").write_text("A_SECRET=y\n", encoding="utf-8")
    (root / "packages" / "a" / "config").mkdir()
    (root / "packages" / "a" / "config" / "settings.yaml").write_text("logging: true\n", encoding="utf-8")
    return root


def test_coverage_reports_discovered_and_inspected_counts(tmp_path: Path):
    root = _make_monorepo(tmp_path)
    config = MakeWikiConfig.default(root)
    collector = EvidenceCollector(config)
    evidence = collector.collect(root, _detect(ProjectType.PYTHON_CLI, "monorepo"))

    cov = evidence.coverage
    # The census must have seen real files.
    assert cov.files_discovered > 0
    assert cov.files_by_category.get("source", 0) >= 1
    assert cov.files_by_category.get("doc", 0) >= 1
    # Anything actually read is reported as inspected-by-tool.
    assert len(cov.files_inspected_by_tool) > 0
    assert isinstance(cov.files_inspected_by_tool, list)


def test_coverage_finds_nested_config_and_scripts(tmp_path: Path):
    root = _make_monorepo(tmp_path)
    config = MakeWikiConfig.default(root)
    collector = EvidenceCollector(config)
    evidence = collector.collect(root, _detect(ProjectType.PYTHON_CLI, "monorepo"))

    cov = evidence.coverage
    # Nested config must surface (recursive globs): packages/a/config/settings.yaml.
    assert any("settings.yaml" in c for c in cov.configs_found), cov.configs_found
    # Manifests from both packages.
    assert any("pyproject.toml" in m for m in cov.manifests_found), cov.manifests_found
    # Makefile is a recognized build script / entrypoint.
    assert any("makefile" in e for e in cov.entrypoints_found), cov.entrypoints_found


def test_coverage_js_ts_source_intelligence_runs(tmp_path: Path):
    root = _make_monorepo(tmp_path)
    config = MakeWikiConfig.default(root)
    collector = EvidenceCollector(config)
    evidence = collector.collect(root, _detect(ProjectType.PYTHON_CLI, "monorepo"))

    # JS/TS files exist; the mechanical pass must have walked them (no longer
    # a silently-skipped ecosystem) and not flagged them uncovered.
    cov = evidence.coverage
    assert "javascript" not in cov.uncovered_categories, cov.uncovered_categories
    assert "typescript" not in cov.uncovered_categories, cov.uncovered_categories
    js_facts = [f for f in evidence.facts if f.fact_type == "command" and "JAVASCRIPT" in f.claim or "TYPESCRIPT" in f.claim]
    assert len(js_facts) > 0, "JS/TS source intelligence should produce facts"


def test_max_files_cap_records_skipped_and_uncovered(tmp_path: Path):
    root = tmp_path / "cap"
    root.mkdir()
    (root / "README.md").write_text("# cap\n", encoding="utf-8")
    # Enough Python source files to exceed a tiny max_files cap.
    for i in range(5):
        (root / f"mod{i}.py").write_text(f"def f{i}(): return {i}\n", encoding="utf-8")

    config = MakeWikiConfig.default(root)
    config.scan.enable_source_intelligence = True
    config.scan.source_intelligence_max_files = 2

    collector = EvidenceCollector(config)
    evidence = collector.collect(root, _detect(ProjectType.PYTHON_CLI, "cap"))

    cov = evidence.coverage
    # Silent truncation must now be visible to the LLM Scout layer.
    assert cov.skipped_due_to_max_files > 0, "max_files cap must be recorded"
    assert "python" in cov.uncovered_categories, (
        "a capped pass must declare its language uncovered"
    )
