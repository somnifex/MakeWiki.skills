"""Data models used during document generation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from makewiki_skills.scanner.project_detector import ProjectType
from makewiki_skills.toolkit.evidence import EvidenceLink


class ProjectIdentity(BaseModel):
    name: str = ""
    version: str | None = None
    tagline: str | None = None
    description: str | None = None
    license: str | None = None
    homepage_url: str | None = None
    repo_url: str | None = None
    authors: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class Prerequisite(BaseModel):
    name: str
    version_constraint: str | None = None
    install_hint: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class InstallStep(BaseModel):
    order: int
    title: str
    commands: list[str] = Field(default_factory=list)
    platform: str | None = None  # None = all
    notes: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class InstallationGuide(BaseModel):
    prerequisites: list[Prerequisite] = Field(default_factory=list)
    steps: list[InstallStep] = Field(default_factory=list)
    verify_command: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class ConfigItem(BaseModel):
    key: str
    value_type: str = "string"
    default_value: str | None = None
    description: str | None = None
    required: bool = False
    source_file: str | None = None
    example_value: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class ConfigSection(BaseModel):
    name: str
    description: str | None = None
    items: list[ConfigItem] = Field(default_factory=list)
    config_file: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class EnvVar(BaseModel):
    """Environment variable configuration."""

    name: str
    description: str | None = None
    default_value: str | None = None
    required: bool = False
    example_value: str | None = None
    source_file: str = ".env.example"
    evidence: list[EvidenceLink] = Field(default_factory=list)


class CommandParam(BaseModel):
    name: str
    param_type: str = "option"  # "argument" | "option" | "flag"
    required: bool = False
    description: str | None = None
    default_value: str | None = None


class Command(BaseModel):
    name: str
    synopsis: str = ""
    description: str | None = None
    section: str | None = None
    source_file: str | None = None
    params: list[CommandParam] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class UserTask(BaseModel):
    task_id: str = ""
    title: str
    user_goal: str = ""
    is_quick_start: bool = Field(
        default=False,
        description=(
            "LLM-authored flag. When True, this task is the canonical quick-start / "
            "getting-started task and may be surfaced as such. Python never infers "
            "this from the title."
        ),
    )
    steps: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    expected_output: str | None = None
    related_config: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class UsageExample(BaseModel):
    title: str
    description: str | None = None
    is_quick_start: bool = Field(
        default=False,
        description=(
            "LLM-authored flag. When True, this example is the canonical quick-start / "
            "getting-started example and may be surfaced as such. Python never infers "
            "this from the title."
        ),
    )
    commands: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class PlatformNote(BaseModel):
    platform: str
    note: str
    evidence: list[EvidenceLink] = Field(default_factory=list)


class FAQItem(BaseModel):
    question: str
    answer: str
    tags: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class TroubleshootingItem(BaseModel):
    symptom: str
    probable_cause: str | None = None
    solution: str
    commands: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class CompatibilityEntry(BaseModel):
    """OS and runtime compatibility entry."""

    os_name: str
    runtime_version: str
    status: str = "supported"  # "supported" | "compatible" | "unsupported" | "untested"
    notes: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class HealthCheck(BaseModel):
    """Post-deployment health check or smoke test command."""

    name: str
    command: str
    expected_output: str | None = None
    description: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class DeploymentNote(BaseModel):
    """Enterprise deployment or runbook procedure."""

    title: str
    target_env: str = "production"
    description: str
    steps: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class LogPathEntry(BaseModel):
    """Log and diagnostic file path information."""

    name: str
    default_path: str
    description: str | None = None
    rotation_policy: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)


class CommandGroup(BaseModel):
    """Group related commands and tasks under one usage page.

    Command groups are an LLM-authored structural decision (how commands and
    tasks cluster into coherent workflows). Python never invents them.
    """

    name: str
    slug: str  # used for filename: usage/<slug>.md
    description: str | None = None
    commands: list[Command] = Field(default_factory=list)
    user_tasks: list[UserTask] = Field(default_factory=list)
    usage_examples: list[UsageExample] = Field(default_factory=list)
    config_sections: list[ConfigSection] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class SemanticModelProvenance(BaseModel):
    """Records which plane populated each part of the SemanticModel.

    ``python`` fields are populated deterministically from extracted evidence.
    ``llm`` fields are authored by LLM subagents and never invented by Python.
    ``unknown`` marks a section Python could not prove — Python returns
    UNKNOWN instead of guessing.
    """

    source: Literal["llm", "python", "hybrid", "unknown"] = "hybrid"
    # Per-section provenance for the LLM-authored content fields.
    identity: Literal["python", "llm", "unknown"] = "unknown"
    installation: Literal["python", "llm", "unknown"] = "unknown"
    configuration: Literal["python", "llm", "unknown"] = "unknown"
    commands: Literal["python", "llm", "unknown"] = "unknown"
    user_tasks: Literal["llm", "unknown"] = "unknown"
    usage_examples: Literal["llm", "unknown"] = "unknown"
    faq: Literal["llm", "unknown"] = "unknown"
    troubleshooting: Literal["llm", "unknown"] = "unknown"
    platform_notes: Literal["llm", "unknown"] = "unknown"
    command_groups: Literal["llm", "unknown"] = "unknown"
    compatibility_matrix: Literal["llm", "unknown"] = "unknown"
    health_checks: Literal["llm", "unknown"] = "unknown"
    deployment_notes: Literal["llm", "unknown"] = "unknown"
    log_paths: Literal["llm", "unknown"] = "unknown"


class SemanticModel(BaseModel):
    """Structured project model used to render docs.

    ``identity``/``installation``/``configuration``/``commands`` may be populated
    deterministically by Python when evidence exists. All *cognitive* fields —
    ``user_tasks``, ``usage_examples``, ``faq``, ``platform_notes``,
    ``troubleshooting``, ``command_groups``, ``compatibility_matrix``,
    ``health_checks``, ``deployment_notes``, ``log_paths``, ``env_vars`` — are
    LLM-authored input. Python validates their schema, renders them, and
    verifies them, but never synthesizes their content.
    """

    model_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    provenance: SemanticModelProvenance = Field(default_factory=SemanticModelProvenance)

    identity: ProjectIdentity = Field(default_factory=ProjectIdentity)
    installation: InstallationGuide = Field(default_factory=InstallationGuide)
    configuration: list[ConfigSection] = Field(default_factory=list)
    env_vars: list[EnvVar] = Field(default_factory=list)
    commands: list[Command] = Field(default_factory=list)
    user_tasks: list[UserTask] = Field(default_factory=list)
    usage_examples: list[UsageExample] = Field(default_factory=list)
    faq: list[FAQItem] = Field(default_factory=list)
    platform_notes: list[PlatformNote] = Field(default_factory=list)
    troubleshooting: list[TroubleshootingItem] = Field(default_factory=list)
    command_groups: list[CommandGroup] = Field(default_factory=list)
    compatibility_matrix: list[CompatibilityEntry] = Field(default_factory=list)
    health_checks: list[HealthCheck] = Field(default_factory=list)
    deployment_notes: list[DeploymentNote] = Field(default_factory=list)
    log_paths: list[LogPathEntry] = Field(default_factory=list)

    project_type: ProjectType = ProjectType.GENERIC
    evidence_summary: dict[str, int] = Field(default_factory=dict)

    def to_context_dict(self) -> dict[str, Any]:
        """Return a template-friendly dict representation."""
        return self.model_dump()
