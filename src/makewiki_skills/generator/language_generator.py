"""Render documents from the semantic model."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jinja2
from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.languages.profile import LanguageProfile
from makewiki_skills.model.semantic_model import SemanticModel


class GeneratedDocument(BaseModel):
    """A single rendered Markdown document for one language."""

    filename: str  # e.g. "README.md" or "README.zh-CN.md"
    base_name: str  # e.g. "README.md" (without language suffix)
    language_code: str
    content: str
    word_count: int = 0
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


DOCUMENT_TEMPLATES: list[tuple[str, str]] = [
    ("README.md", "base/README.md.j2"),
    ("getting-started.md", "base/getting-started.md.j2"),
    ("installation.md", "base/installation.md.j2"),
    ("configuration.md", "base/configuration.md.j2"),
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


class LanguageGenerator:
    """Render the full document set for one language."""

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
        preferred_example = next(
            (example for example in model.usage_examples if "start" in example.title.lower()),
            None,
        )
        preferred_task = next(
            (task for task in model.user_tasks if "start" in task.title.lower()),
            None,
        )
        if preferred_example is not None:
            quick_start_example = preferred_example.model_dump()
        elif preferred_task is not None:
            quick_start_example = {
                "title": preferred_task.title,
                "description": preferred_task.user_goal,
                "commands": preferred_task.commands,
            }
        elif model.usage_examples:
            quick_start_example = model.usage_examples[0].model_dump()
        elif model.user_tasks:
            task = model.user_tasks[0]
            quick_start_example = {
                "title": task.title,
                "description": task.user_goal,
                "commands": task.commands,
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
                    "No specific prerequisites were found in the scanned project files.",
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_config": self._uncertainty(
                    profile,
                    "No user-facing configuration was found in the scanned project files.",
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_faq": self._uncertainty(
                    profile,
                    "No recurring questions stood out in the scanned project files. "
                    "Check the repository discussions for more context.",
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_troubleshooting": self._uncertainty(
                    profile,
                    "No common failure patterns were found in the scanned project files.",
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_usage": self._uncertainty(
                    profile,
                    "No repeatable usage patterns were clear from the scanned project files.",
                    config.emit_uncertainty_notes,
                ),
                "uncertainty_no_platform_notes": self._uncertainty(
                    profile,
                    "No platform-specific notes were found in the scanned project files.",
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

    _SIMPLE_TRANSLATIONS: dict[str, dict[str, str]] = {
        "zh-CN": {
            "Configuration file": "\u914d\u7f6e\u6587\u4ef6",
            "Expected output": "\u9884\u671f\u8f93\u51fa",
            "Key": "\u914d\u7f6e\u9879",
            "No specific prerequisites were found in the scanned project files.": "\u626b\u63cf\u5230\u7684\u9879\u76ee\u6587\u4ef6\u91cc\u6ca1\u6709\u660e\u786e\u7ed9\u51fa\u7279\u5b9a\u524d\u7f6e\u6761\u4ef6\u3002",
            "No user-facing configuration was found in the scanned project files.": "\u626b\u63cf\u5230\u7684\u9879\u76ee\u6587\u4ef6\u91cc\u6ca1\u6709\u8bc6\u522b\u51fa\u9762\u5411\u7528\u6237\u7684\u914d\u7f6e\u9879\u3002",
            "No recurring questions stood out in the scanned project files. Check the repository discussions for more context.": "\u626b\u63cf\u5230\u7684\u9879\u76ee\u6587\u4ef6\u91cc\u6ca1\u6709\u6c89\u6dc0\u51fa\u660e\u786e\u7684\u5e38\u89c1\u95ee\u9898\uff0c\u53ef\u4ee5\u518d\u67e5\u770b\u4ed3\u5e93\u91cc\u7684 issue \u6216\u8ba8\u8bba\u533a\u3002",
            "No common failure patterns were found in the scanned project files.": "\u626b\u63cf\u5230\u7684\u9879\u76ee\u6587\u4ef6\u91cc\u6ca1\u6709\u53d1\u73b0\u660e\u663e\u7684\u5e38\u89c1\u6545\u969c\u6a21\u5f0f\u3002",
            "No repeatable usage patterns were clear from the scanned project files.": "\u626b\u63cf\u5230\u7684\u9879\u76ee\u6587\u4ef6\u91cc\u6ca1\u6709\u63d0\u70bc\u51fa\u7a33\u5b9a\u7684\u4f7f\u7528\u6d41\u7a0b\u3002",
            "No platform-specific notes were found in the scanned project files.": "\u626b\u63cf\u5230\u7684\u9879\u76ee\u6587\u4ef6\u91cc\u6ca1\u6709\u53d1\u73b0\u660e\u663e\u7684\u5e73\u53f0\u5dee\u5f02\u8bf4\u660e\u3002",
            "Platform": "\u5e73\u53f0",
            "Usage Examples": "\u4f7f\u7528\u793a\u4f8b",
            "Documentation Navigation": "\u6587\u6863\u5bfc\u822a",
            "This guide stays with user-visible behavior and skips internal architecture.": "\u672c\u6307\u5357\u53ea\u805a\u7126\u7528\u6237\u5b9e\u9645\u80fd\u770b\u5230\u548c\u64cd\u4f5c\u7684\u5185\u5bb9\uff0c\u4e0d\u5c55\u5f00\u5185\u90e8\u67b6\u6784\u3002",
            "This page lists runtime configuration only. Build and packaging metadata are left out.": "\u672c\u9875\u53ea\u6574\u7406\u8fd0\u884c\u65f6\u914d\u7f6e\uff0c\u4e0d\u5c55\u5f00\u6784\u5efa\u548c\u6253\u5305\u5143\u6570\u636e\u3002",
        },
        "ja": {
            "Configuration file": "\u8a2d\u5b9a\u30d5\u30a1\u30a4\u30eb",
            "Expected output": "\u671f\u5f85\u3055\u308c\u308b\u51fa\u529b",
            "Key": "\u30ad\u30fc",
            "No specific prerequisites were found in the scanned project files.": "\u30b9\u30ad\u30e3\u30f3\u3057\u305f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb\u304b\u3089\u3001\u660e\u78ba\u306a\u524d\u63d0\u6761\u4ef6\u306f\u78ba\u8a8d\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No user-facing configuration was found in the scanned project files.": "\u30b9\u30ad\u30e3\u30f3\u3057\u305f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb\u304b\u3089\u3001\u30e6\u30fc\u30b6\u30fc\u5411\u3051\u306e\u8a2d\u5b9a\u306f\u78ba\u8a8d\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No recurring questions stood out in the scanned project files. Check the repository discussions for more context.": "\u30b9\u30ad\u30e3\u30f3\u3057\u305f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb\u304b\u3089\u3001\u7e70\u308a\u8fd4\u3057\u51fa\u3066\u304f\u308b\u8cea\u554f\u306f\u898b\u5f53\u305f\u308a\u307e\u305b\u3093\u3067\u3057\u305f\u3002\u8a73\u3057\u304f\u306f\u30ea\u30dd\u30b8\u30c8\u30ea\u306e issue \u3084 discussion \u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
            "No common failure patterns were found in the scanned project files.": "\u30b9\u30ad\u30e3\u30f3\u3057\u305f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb\u304b\u3089\u3001\u5178\u578b\u7684\u306a\u30c8\u30e9\u30d6\u30eb\u306f\u78ba\u8a8d\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No repeatable usage patterns were clear from the scanned project files.": "\u30b9\u30ad\u30e3\u30f3\u3057\u305f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb\u304b\u3089\u3001\u5b9a\u578b\u7684\u306a\u4f7f\u3044\u65b9\u306f\u8aad\u307f\u53d6\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No platform-specific notes were found in the scanned project files.": "\u30b9\u30ad\u30e3\u30f3\u3057\u305f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30d5\u30a1\u30a4\u30eb\u304b\u3089\u3001\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0\u56fa\u6709\u306e\u6ce8\u610f\u70b9\u306f\u78ba\u8a8d\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "Platform": "\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0",
            "Usage Examples": "\u4f7f\u7528\u4f8b",
            "Documentation Navigation": "\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\u30ca\u30d3\u30b2\u30fc\u30b7\u30e7\u30f3",
            "This guide stays with user-visible behavior and skips internal architecture.": "\u3053\u306e\u30ac\u30a4\u30c9\u306f\u30e6\u30fc\u30b6\u30fc\u304c\u76f4\u63a5\u6271\u3046\u5185\u5bb9\u306b\u7d5e\u308a\u3001\u5185\u90e8\u30a2\u30fc\u30ad\u30c6\u30af\u30c1\u30e3\u306b\u306f\u8e0f\u307f\u8fbc\u307f\u307e\u305b\u3093\u3002",
            "This page lists runtime configuration only. Build and packaging metadata are left out.": "\u3053\u306e\u30da\u30fc\u30b8\u3067\u306f\u5b9f\u884c\u6642\u306e\u8a2d\u5b9a\u3060\u3051\u3092\u6271\u3044\u3001\u30d3\u30eb\u30c9\u3084\u30d1\u30c3\u30b1\u30fc\u30b8\u30f3\u30b0\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u306f\u7701\u3044\u3066\u3044\u307e\u3059\u3002",
        },
    }

    @classmethod
    def _uncertainty(cls, profile: LanguageProfile, english: str, enabled: bool = True) -> str:
        if not enabled:
            return ""
        lang_map = cls._SIMPLE_TRANSLATIONS.get(profile.code, {})
        return lang_map.get(english, english)

    @classmethod
    def _localize(cls, profile: LanguageProfile, english: str) -> str:
        lang_map = cls._SIMPLE_TRANSLATIONS.get(profile.code, {})
        return lang_map.get(english, english)
