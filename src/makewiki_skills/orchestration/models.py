"""Pydantic models for MakeWiki run artifacts and orchestration state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from makewiki_skills.toolkit.evidence import EvidenceFact

JobKind = Literal[
    "llm-scan",
    "surface-card",
    "semantic-root",
    "module-brief",
    "workflow-brief",
    "page-plan",
    "page-write",
    "page-repair",
]
JobStatus = Literal["pending", "done", "failed", "stale"]


class EvidenceShard(BaseModel):
    """A compact shard of objective evidence, usually grouped by source file."""

    shard_id: str
    source_path: str
    artifact_path: str
    fact_types: list[str] = Field(default_factory=list)
    facts: list[EvidenceFact] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def fact_count(self) -> int:
        return len(self.facts)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def confidence_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for fact in self.facts:
            summary[fact.best_confidence] = summary.get(fact.best_confidence, 0) + 1
        return summary


class EvidenceIndex(BaseModel):
    """Top-level index pointing to all objective evidence shards in a run."""

    run_id: str
    project_root: str
    project_name: str
    project_type: str
    detection_confidence: float
    artifact_dir: str
    collection_mode: Literal["python", "llm-fallback"] = "python"
    fallback_reason: str | None = None
    files_read: list[str] = Field(default_factory=list)
    fact_summary: dict[str, int] = Field(default_factory=dict)
    shards: list[EvidenceShard] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def shard_count(self) -> int:
        return len(self.shards)


class ModuleIndexItem(BaseModel):
    """Minimal module index item that the main conversation is allowed to load."""

    id: str
    name: str


class WorkflowIndexItem(BaseModel):
    """Minimal workflow index item that references related modules by id."""

    id: str
    name: str
    module_ids: list[str] = Field(default_factory=list)


class PageIndexItem(BaseModel):
    """Minimal page index item used by the orchestrator to plan work."""

    id: str
    kind: str
    scope: str
    target_ids: list[str] = Field(default_factory=list)


class SemanticModelIndex(BaseModel):
    """Index-only semantic view exposed to the main conversation."""

    run_id: str
    languages: list[str] = Field(default_factory=list)
    modules: list[ModuleIndexItem] = Field(default_factory=list)
    workflows: list[WorkflowIndexItem] = Field(default_factory=list)
    pages: list[PageIndexItem] = Field(default_factory=list)


class PagePlan(BaseModel):
    """Language-agnostic page plan authored by the LLM."""

    page_id: str
    output_path: str
    kind: str
    scope: str
    target_ids: list[str] = Field(default_factory=list)


class ChildSkillReceipt(BaseModel):
    """Short receipt emitted by child skills back to the orchestrator."""

    job_id: str
    status: Literal["done", "failed"]
    artifact_path: str
    trace_path: str
    error_code: str | None = None
    attempt: int = 1


class RunJob(BaseModel):
    """A resumable unit of work inside a run."""

    job_id: str
    kind: JobKind
    status: JobStatus = "pending"
    module_id: str | None = None
    workflow_id: str | None = None
    page_id: str | None = None
    language_code: str | None = None
    source_ref: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    artifact_path: str | None = None
    trace_path: str | None = None
    receipt_path: str | None = None
    attempt: int = 0
    error_code: str | None = None


class RunState(BaseModel):
    """Persisted state for an orchestration run."""

    run_id: str
    project_root: str
    output_dir: str
    max_attempts: int
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    jobs: list[RunJob] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def job_counts(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for job in self.jobs:
            key = f"{job.kind}:{job.status}"
            summary[key] = summary.get(key, 0) + 1
        return summary
