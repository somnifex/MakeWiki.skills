"""Legacy deterministic renderer for the Mechanical Plane.

This module is the **non-authoritative** scaffold that renders documents from a
``SemanticModel`` via Jinja templates. It is NOT the authoritative MakeWiki
writer — the authoritative writer is the LLM Language Writer subagent (see
``SKILL.md``). It is reachable only through the deprecated ``legacy-generate``
/ ``generate`` CLI path.

The neutral document model lives in ``model.document_artifact``; this module
re-exports it so historically-importing callers keep working while the
codebase migrates to the neutral name.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.languages.profile import LanguageProfile
from makewiki_skills.model.document_artifact import (
    DocumentArtifact,
    GeneratedDocument,
)
from makewiki_skills.model.semantic_model import SemanticModel

# Backward-compatible aliases so existing import sites keep working during the
# migration to the neutral names.
RenderedDocument = DocumentArtifact
Document = DocumentArtifact

# Canonical English UNKNOWN markers and neutral labels.
#
# These are the ONLY narrative-leaning strings the deterministic scaffold may
# emit, and they are deliberately English-only. Python does not translate
# narrative — localization of prose (including these honest UNKNOWN
# markers) is the LLM Language Writer's job in the authoritative /makewiki
# flow. When a slot cannot be mechanically proven, the scaffold emits the
# canonical English marker below (or nothing at all) rather than fabricating
# per-language prose.
UNKNOWN_PREREQ_MARKER = (
    "No specific prerequisites were found in the scanned project files."
)
UNKNOWN_CONFIG_MARKER = (
    "No user-facing configuration was found in the scanned project files."
)
UNKNOWN_FAQ_MARKER = (
    "No recurring questions stood out in the scanned project files. "
    "Check the repository discussions for more context."
)
UNKNOWN_TROUBLESHOOTING_MARKER = (
    "No common failure patterns were found in the scanned project files."
)
UNKNOWN_QUICK_START_MARKER = (
    "No explicit quick-start example was identified for this project."
)
UNKNOWN_USAGE_MARKER = (
    "No repeatable usage patterns were clear from the scanned project files."
)
UNKNOWN_PLATFORM_NOTE_MARKER = (
    "No platform-specific notes were found in the scanned project files."
)


DOCUMENT_TEMPLATES: list[tuple[str, str]] = [
    ("README.md", "base/README.md.j2"),
    ("getting-started.md", "base/getting-started.md.j2"),
    ("installation.md", "base/installation.md.j2"),
    ("configuration.md", "base/configuration.md.j2"),
    ("environment-variables.md", "base/environment-variables.md.j2"),
    ("faq.md", "base/faq.md.j2"),
    ("troubleshooting.md", "base/troubleshooting.md.j2"),
    ("usage/basic-usage.md", "base/usage/basic-usage.md.j2"),
]


def _resolve_templates(
    model: SemanticModel,
    config: MakeWikiConfig,
) -> list[tuple[str, str, dict[str, Any]]]:
    """Return the pages that should be rendered for this model."""
    pages: list[tuple[str, str, dict[str, Any]]] = []

    for base_name, template_path in DOCUMENT_TEMPLATES:
        if base_name == "faq.md" and not config.generate_faq:
            continue
        if base_name == "troubleshooting.md" and not config.generate_troubleshooting:
            continue
        if base_name == "environment-variables.md" and not config.generate_env_vars_page:
            continue
        if base_name == "usage/basic-usage.md" and model.command_groups:
            pages.append(
                (
                    "usage/overview.md",
                    "base/usage/overview.md.j2",
                    {},
                )
            )
            for group in model.command_groups:
                pages.append(
                    (
                        f"usage/{group.slug}.md",
                        "base/usage/module-page.md.j2",
                        {"current_group": group.model_dump()},
                    )
                )
            continue
        pages.append((base_name, template_path, {}))

    return pages


class LegacyDeterministicRenderer:
    """Render the full document set for one language.

    **Legacy / non-authoritative.** The canonical writer in the authoritative
    ``/makewiki`` flow is the LLM Language Writer subagent. This Jinja-based
    renderer is the deprecated deterministic scaffold, kept for regression
    testing and mechanical fallback only.
    """

    def __init__(self, template_dir: Path | None = None) -> None:
        if template_dir is None:
            template_dir = Path(__file__).resolve().parent.parent / "templates"
        self._template_dir = template_dir
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self._template_dir)),
            undefined=jinja2.Undefined,
            keep_trailing_newline=True,
        )

    def generate(
        self,
        model: SemanticModel,
        profile: LanguageProfile,
        config: MakeWikiConfig,
    ) -> list[GeneratedDocument]:
        context = self._build_context(model, profile, config)
        documents: list[GeneratedDocument] = []

        for base_name, template_path, extra_ctx in _resolve_templates(model, config):
            merged = {**context, **extra_ctx}
            content = self._render(template_path, merged)
            content = self._apply_formatting(content, profile)
            filename = profile.get_filename(base_name)

            documents.append(
                GeneratedDocument(
                    filename=filename,
                    base_name=base_name,
                    language_code=profile.code,
                    content=content,
                    word_count=len(content.split()),
                )
            )

        return documents

    def _build_context(
        self,
        model: SemanticModel,
        profile: LanguageProfile,
        config: MakeWikiConfig,
    ) -> dict[str, Any]:
        """Build the template context for one language."""
        terms = profile.terminology
        formatting = profile.formatting

        def _link(base: str) -> str:
            return profile.get_filename(base)

        quick_start_example: dict[str, Any] | None = None
        # A quick-start item is chosen ONLY by the explicit ``is_quick_start``
        # flag (LLM-authored). Python never guesses a quick-start by matching
        # the word "start" in a title — that is a semantic decision. When no
        # item is explicitly flagged, an honest UNKNOWN marker is rendered
        # instead (or nothing at all when uncertainty notes are disabled).
        flagged_example = next(
            (example for example in model.usage_examples if example.is_quick_start),
            None,
        )
        flagged_task = next(
            (task for task in model.user_tasks if task.is_quick_start),
            None,
        )
        if flagged_example is not None:
            quick_start_example = flagged_example.model_dump()
        elif flagged_task is not None:
            quick_start_example = {
                "title": flagged_task.title,
                "description": flagged_task.user_goal,
                "commands": flagged_task.commands,
            }
        elif config.emit_uncertainty_notes:
            quick_start_example = {
                "title": self._uncertainty(
                    profile,
                    UNKNOWN_QUICK_START_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "description": None,
                "commands": [],
            }

        ctx = model.to_context_dict()
        ctx.update(
            {
                "terms": terms.model_dump(),
                "formatting": formatting.model_dump(),
                "language_code": profile.code,
                "language_name": profile.display_name,
                "getting_started_link": _link("getting-started.md"),
                "installation_link": _link("installation.md"),
                "configuration_link": _link("configuration.md"),
                "usage_link": (
                    "usage/" + _link("overview.md")
                    if model.command_groups
                    else "usage/" + _link("basic-usage.md")
                ),
                "faq_link": _link("faq.md"),
                "troubleshooting_link": _link("troubleshooting.md"),
                "readme_link": _link("README.md"),
                "index_link": "index.md",
                "has_faq": config.generate_faq and len(model.faq) > 0,
                "has_troubleshooting": config.generate_troubleshooting
                and len(model.troubleshooting) > 0,
                "has_usage_examples": len(model.usage_examples) > 0,
                "has_platform_notes": len(model.platform_notes) > 0,
                "has_command_groups": len(model.command_groups) > 0,
                "command_groups": [g.model_dump() for g in model.command_groups],
                "command_group_links": [
                    {
                        "name": g.name,
                        "slug": g.slug,
                        "link": "usage/" + _link(f"{g.slug}.md"),
                    }
                    for g in model.command_groups
                ],
                "quick_start_example": quick_start_example,
                "uncertainty_no_prereqs": self._uncertainty(
                    profile,
                    UNKNOWN_PREREQ_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_config": self._uncertainty(
                    profile,
                    UNKNOWN_CONFIG_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_faq": self._uncertainty(
                    profile,
                    UNKNOWN_FAQ_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_troubleshooting": self._uncertainty(
                    profile,
                    UNKNOWN_TROUBLESHOOTING_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_usage": self._uncertainty(
                    profile,
                    UNKNOWN_USAGE_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_platform_notes": self._uncertainty(
                    profile,
                    UNKNOWN_PLATFORM_NOTE_MARKER,
                    config.emit_uncertainty_notes,
                ),
                "config_file_label": self._localize(profile, "Configuration file"),
                "expected_output_label": self._localize(profile, "Expected output"),
                "key": self._localize(profile, "Key"),
                "platform_label": self._localize(profile, "Platform"),
                "usage_examples_heading": self._localize(profile, "Usage Examples"),
                "documentation_navigation_heading": self._localize(
                    profile, "Documentation Navigation"
                ),
                "user_focus_note": self._localize(
                    profile,
                    "This guide stays with user-visible behavior and skips internal architecture.",
                ),
                "user_config_note": self._localize(
                    profile,
                    "This page lists runtime configuration only. Build and packaging metadata are left out.",
                ),
            }
        )

        for k, v in terms.model_dump().items():
            ctx[f"terms_{k}"] = v

        return ctx

    def _render(self, template_path: str, context: dict[str, Any]) -> str:
        template = self._env.get_template(template_path)
        return template.render(**context)

    def _apply_formatting(self, content: str, profile: LanguageProfile) -> str:
        if profile.formatting.space_between_cjk_and_latin:
            content = self._add_cjk_latin_spaces(content)
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        return content.strip() + "\n"

    @staticmethod
    def _add_cjk_latin_spaces(text: str) -> str:
        import re

        cjk = r"[\u4e00-\u9fff\u3400-\u4dbf]"
        latin = r"[a-zA-Z0-9]"
        text = re.sub(f"({cjk})({latin})", r"\1 \2", text)
        text = re.sub(f"({latin})({cjk})", r"\1 \2", text)
        return text

    @classmethod
    def _uncertainty(cls, profile: LanguageProfile, english: str, enabled: bool = True) -> str:
        """Return the honest UNKNOWN marker for a slot.

        This is deliberately English-only: Python does not translate narrative.
        Localization of these markers and labels is the LLM Language Writer's
        job in the authoritative /makewiki flow. When a slot cannot be
        mechanically proven it emits the single canonical English marker, never
        Python-authored per-language prose.
        """
        del profile
        if not enabled:
            return ""
        return english

    @classmethod
    def _localize(cls, profile: LanguageProfile, english: str) -> str:
        """Return the neutral English label.

        Python no longer carries a per-language translation table: the labels
        stay English and localization is delegated to the LLM writer.
        """
        del profile
        return english


# Backward-compatible alias: the canonical name is
# ``LegacyDeterministicRenderer`` (an explicitly non-authoritative scaffold).
# ``LanguageGenerator`` is retained so existing imports, tests and call sites
# keep functioning while the codebase migrates to the legacy-stated name.
LanguageGenerator = LegacyDeterministicRenderer
