"""Mechanical coverage report for a repository discovery pass.

The :mod:`EvidenceCollector` walks a project deterministically. This module
defines the *coverage* view of that walk — what was discovered, what was
inspected, what was skipped and why, and what the mechanical plane did **not**
touch. It is pure bookkeeping: it never attaches meaning to the repository.

The report is deliberately split into two halves across the Cognitive
Authority Boundary:

- The **mechanical** fields (:attr:`CoverageReport.files_discovered`,
  ``files_inspected_by_tool``, ``files_skipped``, ``ignored_files``,
  ``entrypoints_found``, ``configs_found``, ``tests_inspected``,
  ``manifests_found``, ``generated_code_boundaries``,
  ``skipped_due_to_max_files``) are PROVEN by the toolkit.
- :attr:`CoverageReport.uncovered_categories` is the mechanical plane telling
  the LLM Scout layer which categories the walk did *not* penetrate (e.g. JS/TS
  source intelligence is gated on project type, nested configs are not
  surfaced). The LLM owns acting on those gaps; Python only declares them.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CoverageReport(BaseModel):
    """Aggregate mechanical coverage of a repository discovery pass.

    No semantic judgment: every field is a deterministic count or an explicit
    list of what was / was not inspected. Low-confidence facts are surfaced for
    the LLM to adjudicate, never resolved here.
    """

    files_discovered: int = 0
    files_by_category: dict[str, int] = Field(default_factory=dict)
    files_inspected_by_tool: list[str] = Field(default_factory=list)
    files_skipped: list[dict[str, str]] = Field(
        default_factory=list,
        description="Each item: {'path', 'reason'} where reason is one of "
        "ignore_dirs | max_depth | max_size | max_files_cap | extension",
    )
    ignored_files: list[str] = Field(default_factory=list)
    entrypoints_found: list[str] = Field(default_factory=list)
    configs_found: list[str] = Field(default_factory=list)
    tests_inspected: list[str] = Field(default_factory=list)
    manifests_found: list[str] = Field(default_factory=list)
    generated_code_boundaries: list[str] = Field(default_factory=list)
    uncovered_categories: list[str] = Field(default_factory=list)
    low_confidence_facts: list[str] = Field(default_factory=list)
    skipped_due_to_max_files: int = 0
