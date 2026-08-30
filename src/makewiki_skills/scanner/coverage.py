"""Mechanical coverage report for a repository discovery pass.

The :mod:`EvidenceCollector` walks a project deterministically. This module
defines the *coverage* view of that walk — what was discovered, what was
inspected, what was read, what was parsed, what was skipped and why, and what
the mechanical plane did **not** touch. It is pure bookkeeping: it never
attaches meaning to the repository.

All extractors isolate exceptions independently, recording granular tool health
and failure records without crashing the collection pass.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolFailureRecord(BaseModel):
    """An isolated exception or parsing failure from a mechanical extractor."""

    extractor: str
    source_path: str
    error_type: str
    message: str


class CoverageReport(BaseModel):
    """Aggregate mechanical coverage of a repository discovery pass.

    No semantic judgment: every field is a deterministic count or an explicit
    list of what was / was not inspected. Tool failures and unverified items
    are recorded as raw facts.
    """

    files_discovered: int = 0
    files_read: int = 0
    files_parsed: int = 0
    files_with_facts: int = 0

    tests_discovered: int = 0
    tests_read: int = 0  # of the files actually read this pass, how many were tests

    configs_discovered: int = 0
    configs_read: int = 0

    manifests_discovered: int = 0
    manifests_read: int = 0  # of the files actually read this pass, how many were manifests

    files_by_category: dict[str, int] = Field(default_factory=dict)
    files_inspected_by_tool: list[str] = Field(default_factory=list)
    files_skipped: list[dict[str, str]] = Field(
        default_factory=list,
        description="Each item: {'path', 'reason'} where reason is one of "
        "ignore_dirs | max_depth | max_size | max_files_cap | extension",
    )
    ignored_files: list[str] = Field(
        default_factory=list,
        description="Relative paths of subtrees/files the walk pruned in-place "
        "(ignored dirs and files beneath them). Populated during the census walk.",
    )
    entrypoints_found: list[str] = Field(default_factory=list)
    configs_found: list[str] = Field(default_factory=list)
    tests_inspected: list[str] = Field(default_factory=list)
    manifests_found: list[str] = Field(default_factory=list)
    generated_code_boundaries: list[str] = Field(default_factory=list)
    uncovered_categories: list[str] = Field(default_factory=list)
    mechanically_uncovered_ecosystems: list[str] = Field(
        default_factory=list,
        description="Ecosystems present in the repo (e.g. 'python', 'go') whose "
        "source intelligence pass did not run this scan — their semantics were "
        "not mechanically parsed. Distinct from uncovered_categories (scan-budget)"
        " and from uncovered semantic categories.",
    )
    low_confidence_facts: list[str] = Field(default_factory=list)
    skipped_due_to_max_files: int = 0

    # Fail-soft tool health and failure diagnostics
    tool_failures: list[ToolFailureRecord] = Field(default_factory=list)
    tool_health: dict[str, str] = Field(
        default_factory=dict,
        description="Health status per tool/extractor: 'OK' | 'DEGRADED' | 'TOOL_ERROR'",
    )
