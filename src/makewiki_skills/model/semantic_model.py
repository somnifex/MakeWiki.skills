"""Language-neutral document model built from collected evidence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
    steps: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    expected_output: str | None = None
    related_config: list[str] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)

class UsageExample(BaseModel):
    title: str
    description: str | None = None
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


class CommandGroup(BaseModel):
    """A logical grouping of commands/tasks for modular documentation.

    When a project is complex enough, commands are organized into groups
    so each group can be documented on its own sub-page under usage/.
    """

    name: str
    slug: str  # used for filename: usage/<slug>.md
    description: str | None = None
    commands: list[Command] = Field(default_factory=list)
    user_tasks: list[UserTask] = Field(default_factory=list)
    usage_examples: list[UsageExample] = Field(default_factory=list)
    config_sections: list[ConfigSection] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)

class SemanticModel(BaseModel):
    """The complete, language-neutral document model."""

    model_id: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    identity: ProjectIdentity = Field(default_factory=ProjectIdentity)
    installation: InstallationGuide = Field(default_factory=InstallationGuide)
    configuration: list[ConfigSection] = Field(default_factory=list)
    commands: list[Command] = Field(default_factory=list)
    user_tasks: list[UserTask] = Field(default_factory=list)
    usage_examples: list[UsageExample] = Field(default_factory=list)
    faq: list[FAQItem] = Field(default_factory=list)
    platform_notes: list[PlatformNote] = Field(default_factory=list)
    troubleshooting: list[TroubleshootingItem] = Field(default_factory=list)
    command_groups: list[CommandGroup] = Field(default_factory=list)

    project_type: ProjectType = ProjectType.GENERIC
    evidence_summary: dict[str, int] = Field(default_factory=dict)

    def to_context_dict(self) -> dict[str, Any]:
        """Flatten into a dict suitable for Jinja2 template rendering."""
        return self.model_dump()
