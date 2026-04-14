"""Base models for per-language terminology, formatting, and style."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class FormalityLevel(str, Enum):
    FORMAL = "formal"
    NEUTRAL = "neutral"
    CASUAL = "casual"


class TerminologyMap(BaseModel):
    """Maps semantic section names to language-specific labels."""

    installation: str = "Installation"
    configuration: str = "Configuration"
    getting_started: str = "Getting Started"
    prerequisites: str = "Prerequisites"
    usage: str = "Usage"
    basic_usage: str = "Basic Usage"
    commands: str = "Commands"
    faq: str = "FAQ"
    troubleshooting: str = "Troubleshooting"
    note: str = "Note"
    warning: str = "Warning"
    tip: str = "Tip"
    example: str = "Example"
    optional: str = "optional"
    required: str = "required"
    default_value: str = "Default"
    description: str = "Description"
    command: str = "Command"
    question: str = "Question"
    answer: str = "Answer"
    symptom: str = "Symptom"
    solution: str = "Solution"
    cause: str = "Possible Cause"
    next_steps: str = "Next Steps"
    table_of_contents: str = "Table of Contents"
    what_is: str = "What is {name}?"
    who_is_it_for: str = "Who is it for?"
    project_overview: str = "Overview"
    verify_installation: str = "Verify Installation"
    quick_start: str = "Quick Start"
    common_tasks: str = "Common Tasks"
    platform_notes: str = "Platform Notes"
    environment_variables: str = "Environment Variables"
    related_docs: str = "Related Documentation"


class FormattingRules(BaseModel):
    """Language-specific Markdown formatting rules."""

    note_callout: str = "> **Note:**"
    warning_callout: str = "> **Warning:**"
    tip_callout: str = "> **Tip:**"
    list_marker: str = "-"
    date_format: str = "YYYY-MM-DD"
    number_format: str = "1,000"
    use_fullwidth_punctuation: bool = False
    space_between_cjk_and_latin: bool = False


class LanguageProfile(BaseModel):
    """Complete profile for a single language."""

    code: str  # BCP-47: "en", "zh-CN", "ja", "de", "fr"
    display_name: str
    native_name: str
    terminology: TerminologyMap = Field(default_factory=TerminologyMap)
    formality: FormalityLevel = FormalityLevel.NEUTRAL
    formatting: FormattingRules = Field(default_factory=FormattingRules)
    generation_hints: str = ""
    file_suffix: str = ""  # "" for default language, ".zh-CN" etc

    def get_filename(self, base_name: str) -> str:
        """Return the language-suffixed filename.

        For example, base_name="README.md" and suffix=".zh-CN"
        becomes "README.zh-CN.md".
        """
        if not self.file_suffix:
            return base_name
        parts = base_name.rsplit(".", 1)
        if len(parts) == 2:
            return f"{parts[0]}{self.file_suffix}.{parts[1]}"
        return f"{base_name}{self.file_suffix}"
