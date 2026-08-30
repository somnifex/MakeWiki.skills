"""Coverage command + report contract tests.

The `coverage` command is a mechanical-plane addition: deterministic coverage
bookkeeping for the discovery pass. This test asserts the command is
registered, documented in the skill corpus (so it is actually surfaced to the
LLM Scout layer), and that the `CoverageReport` model it emits is the one the
rest of the mechanical plane consumes — no dead or orphaned surface.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.cli import app
from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.scanner.coverage import CoverageReport
from makewiki_skills.scanner.evidence_collector import CollectedEvidence, EvidenceCollector
from makewiki_skills.scanner.project_detector import (
    ProjectDetectionResult,
    ProjectType,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REGISTERED = {
    cmd.name or (cmd.callback.__name__ if cmd.callback else "")
    for cmd in app.registered_commands
}


def test_coverage_command_is_registered():
    assert "coverage" in REGISTERED, "`coverage` must be a registered Typer command"


def test_coverage_is_documented_in_skill_corpus():
    """The coverage command must be surfaced where the LLM Scout layer reads it."""
    docs = [
        PROJECT_ROOT / "SKILL.md",
        PROJECT_ROOT / "subskills" / "scan" / "SKILL.md",
        PROJECT_ROOT / "references" / "api.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert "`coverage`" in text or "coverage ." in text, (
            f"coverage command must be documented in {doc.relative_to(PROJECT_ROOT)}"
        )


def test_collected_evidence_owns_a_coverage_report():
    """The collector's output carries the CoverageReport as the single source."""
    fields = {n for n in CollectedEvidence.model_fields}
    assert "coverage" in fields, "CollectedEvidence must carry a coverage report field"
    default = CollectedEvidence(
        project_dir=".",
        detection=ProjectDetectionResult(
            project_type=ProjectType.GENERIC,
            project_name="x",
            confidence=0.5,
        ),
    )
    assert isinstance(default.coverage, CoverageReport)


def test_coverage_report_exposes_mechanical_keys():
    """Every field the LLM Scout layer needs to reason over is present."""
    required = {
        "files_discovered",
        "files_by_category",
        "files_inspected_by_tool",
        "files_skipped",
        "ignored_files",
        "entrypoints_found",
        "configs_found",
        "tests_inspected",
        "manifests_found",
        "generated_code_boundaries",
        "uncovered_categories",
        "low_confidence_facts",
        "skipped_due_to_max_files",
    }
    present = set(CoverageReport.model_fields)
    missing = required - present
    assert not missing, f"CoverageReport missing contract fields: {sorted(missing)}"


def test_coverage_presence_fields_are_populated_end_to_end(tmp_path: Path):
    """The accounting fields must be *populated* by a real pass, not just declared.

    Regression for the dead-field defect: ignored_files / tests_read /
    manifests_read / skipped_due_to_max_files were declared but never written,
    so the CLI printed permanent zeros that looked like audited coverage.
    """
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "main.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (proj / "tests").mkdir()
    (proj / "tests" / "test_main.py").write_text("def test_run():\n    pass\n", encoding="utf-8")
    (proj / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    # An ignored subtree that the walk must prune in-place:
    (proj / "node_modules").mkdir()
    (proj / "node_modules" / "dep.js").write_text("module.exports = {};\n", encoding="utf-8")

    cfg = MakeWikiConfig.default(proj)
    cfg.scan.ignore_dirs = ["node_modules"]
    collector = EvidenceCollector(cfg)
    detection = ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        project_name="proj",
        project_dir=str(proj),
        confidence=0.9,
    )
    collected = collector.collect(proj, detection)
    cov = collected.coverage

    # ignored_files must actually record the pruned subtree.
    assert any("node_modules" in p for p in cov.ignored_files), (
        f"ignored_files must record pruned node_modules, got {cov.ignored_files}"
    )
    # tests_read counts test files actually read (and cannot exceed discovered).
    assert cov.tests_read >= 1, f"tests_read must be populated, got {cov.tests_read}"
    assert cov.tests_read <= cov.tests_discovered
    # manifests_read counts manifests actually read.
    assert cov.manifests_read >= 1, f"manifests_read must be populated, got {cov.manifests_read}"
    assert cov.manifests_read <= cov.manifests_discovered
