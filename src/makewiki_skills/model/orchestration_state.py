"""Orchestration State Model.

Maintained and owned exclusively by the Main Agent LLM in its context / scratchpad.
Python provides schema validation and serialization helpers only. Python MUST NOT
make scheduling, scoping, or semantic decisions based on this state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.model.documentation_model import DocumentationModel
from makewiki_skills.model.page_spec import PageSpec
from makewiki_skills.model.v3_artifacts import (
    InvestigationPlan,
    RepositoryBrief,
    SubtaskSpec,
)


class AgentRecord(BaseModel):
    """Record of an active or completed subagent."""

    agent_id: str
    role: str
    assigned_scope: str = ""
    dispatched_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    summary: str = ""
    status: str = "running"  # running | completed | failed | canceled


class ClaimRecord(BaseModel):
    """A factual or semantic claim held in the orchestration pool."""

    claim_id: str
    semantic_key: str
    assertion: str
    value: Any = None
    confidence: float = 1.0  # 0.0 to 1.0
    evidence_refs: list[str] = Field(default_factory=list)
    source_agent: str = ""
    provenance: str = "llm_claim"  # python_fact | llm_claim
    hedged: bool = False
    uncertainty_note: str | None = None


class ConflictRecord(BaseModel):
    """A detected conflict between multiple claims or sources."""

    conflict_id: str
    semantic_key: str
    description: str
    competing_claims: list[str] = Field(default_factory=list)  # claim_ids
    sources_involved: list[str] = Field(default_factory=list)
    status: str = "open"  # open | in_debate | resolved | conceded
    resolution: str | None = None


class ToolFailureRecord(BaseModel):
    """Record of a mechanical tool error requiring potential recovery."""

    tool_name: str
    target_path: str = ""
    error_message: str
    recovered_by: str | None = None  # e.g., "Recovery Scout: Direct AST inspection"
    status: str = "unrecovered"  # unrecovered | recovered | ignored


class OrchestrationState(BaseModel):
    """LLM-owned comprehensive runtime orchestration state.

    Main Agent maintains this state across the documentation lifecycle:
    Reconnaissance -> ReBattle -> Writing -> Audit -> Delivery.
    """

    schema_version: str = "1"
    user_goal: str = ""
    repository_understanding: str = ""
    search_plan: list[str] = Field(default_factory=list)
    active_agents: list[AgentRecord] = Field(default_factory=list)
    completed_agents: list[AgentRecord] = Field(default_factory=list)
    coverage_gaps: list[str] = Field(default_factory=list)
    tool_failures: list[ToolFailureRecord] = Field(default_factory=list)
    claims: list[ClaimRecord] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    semantic_model: dict[str, Any] | None = None
    documentation_plan: dict[str, Any] | None = None
    audit_status: dict[str, Any] | None = None
    delivery_status: dict[str, Any] | None = None
    # --- V3 cognitive artifact slots (LLM-authored; Python only stores/validates) ---
    # These hold references to the V3 handoff artifacts. Python does NOT schedule
    # subtasks or choose which one is "ready" — the Main Agent LLM owns that.
    repository_brief: RepositoryBrief | None = None
    investigation_plan: InvestigationPlan | None = None
    subtasks: list[SubtaskSpec] = Field(default_factory=list)
    # ``documentation_model`` and ``page_specs`` are typed V3 artifacts (Phase
    # G / H / I) — stored as actual models, not free dicts.
    documentation_model: DocumentationModel | None = None
    page_specs: list[PageSpec] = Field(default_factory=list)
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self, indent: int = 2) -> str:
        """Serialize state to formatted JSON string."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, data: str | dict[str, Any]) -> OrchestrationState:
        """Parse orchestration state from JSON string or dict."""
        if isinstance(data, str):
            return cls.model_validate_json(data)
        return cls.model_validate(data)
