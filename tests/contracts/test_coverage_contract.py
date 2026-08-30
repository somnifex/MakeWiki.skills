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
from makewiki_skills.scanner.coverage import CoverageReport
from makewiki_skills.scanner.evidence_collector import CollectedEvidence
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
