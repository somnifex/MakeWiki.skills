"""Render one document set per language from the semantic model."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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

class LanguageGenerator:
    """Generate a full document set for a single language.

    Each language is rendered independently from the same semantic model.
    The language profile injects terminology, formatting rules, and style hints.
    No language is used as a base for translation to another.
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
        """Generate all documents for a single language."""
        context = self._build_context(model, profile, config)
        documents: list[GeneratedDocument] = []

        for base_name, template_path in DOCUMENT_TEMPLATES:
            if base_name == "faq.md" and not config.generate_faq:
                continue
            if base_name == "troubleshooting.md" and not config.generate_troubleshooting:
                continue

            content = self._render(template_path, context)
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
    ) -> dict:
        """Combine semantic data with language-specific labels and formatting."""
        terms = profile.terminology
        formatting = profile.formatting

        def _link(base: str) -> str:
            return profile.get_filename(base)

        quick_start_example: dict | None = None
        preferred_example = next(
            (
                example
                for example in model.usage_examples
                if "start" in example.title.lower()
            ),
            None,
        )
        preferred_task = next(
            (
                task
                for task in model.user_tasks
                if "start" in task.title.lower()
            ),
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
                "usage_link": "usage/" + _link("basic-usage.md"),
                "faq_link": _link("faq.md"),
                "troubleshooting_link": _link("troubleshooting.md"),
                "readme_link": _link("README.md"),
                "index_link": "index.md",
                "has_faq": config.generate_faq and len(model.faq) > 0,
                "has_troubleshooting": config.generate_troubleshooting
                and len(model.troubleshooting) > 0,
                "has_usage_examples": len(model.usage_examples) > 0,
                "has_platform_notes": len(model.platform_notes) > 0,
                "quick_start_example": quick_start_example,
                "uncertainty_no_prereqs": self._uncertainty(
                    profile, "No specific prerequisites were identified from the project evidence."
                ),
                "uncertainty_no_config": self._uncertainty(
                    profile, "No configuration items were identified from the project evidence."
                ),
                "uncertainty_no_faq": self._uncertainty(
                    profile,
                    "No frequently asked questions were identified. "
                    "Check the project repository for community discussions.",
                ),
                "uncertainty_no_troubleshooting": self._uncertainty(
                    profile,
                    "No common issues were identified from the project evidence.",
                ),
                "uncertainty_no_usage": self._uncertainty(
                    profile, "No usage patterns were identified from the project evidence."
                ),
                "uncertainty_no_platform_notes": self._uncertainty(
                    profile, "No platform-specific notes were identified from the project evidence."
                ),
                "config_file_label": self._localize(profile, "Configuration file"),
                "expected_output_label": self._localize(profile, "Expected output"),
                "key": self._localize(profile, "Key"),
                "platform_label": self._localize(profile, "Platform"),
                "usage_examples_heading": self._localize(profile, "Usage Examples"),
                "documentation_navigation_heading": self._localize(profile, "Documentation Navigation"),
                "user_focus_note": self._localize(
                    profile,
                    "This documentation focuses on user-visible behavior. Internal architecture and source layout are intentionally omitted.",
                ),
                "user_config_note": self._localize(
                    profile,
                    "Only user-facing configuration files are listed here. Build and packaging metadata are intentionally omitted.",
                ),
            }
        )

        for k, v in terms.model_dump().items():
            ctx[f"terms_{k}"] = v

        return ctx

    def _render(self, template_path: str, context: dict) -> str:
        template = self._env.get_template(template_path)
        return template.render(**context)

    def _apply_formatting(self, content: str, profile: LanguageProfile) -> str:
        """Apply language-specific formatting rules after rendering."""
        if profile.formatting.space_between_cjk_and_latin:
            content = self._add_cjk_latin_spaces(content)
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")
        return content.strip() + "\n"

    @staticmethod
    def _add_cjk_latin_spaces(text: str) -> str:
        """Insert spaces between CJK characters and Latin characters."""
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
            "No specific prerequisites were identified from the project evidence.":
                "\u672a\u4ece\u9879\u76ee\u8bc1\u636e\u4e2d\u8bc6\u522b\u51fa\u7279\u5b9a\u7684\u524d\u7f6e\u6761\u4ef6\u3002",
            "No configuration items were identified from the project evidence.":
                "\u672a\u4ece\u9879\u76ee\u8bc1\u636e\u4e2d\u8bc6\u522b\u51fa\u914d\u7f6e\u9879\u3002",
            "No frequently asked questions were identified. Check the project repository for community discussions.":
                "\u672a\u8bc6\u522b\u51fa\u5e38\u89c1\u95ee\u9898\u3002\u8bf7\u67e5\u770b\u9879\u76ee\u4ed3\u5e93\u4e2d\u7684\u793e\u533a\u8ba8\u8bba\u3002",
            "No common issues were identified from the project evidence.":
                "\u672a\u4ece\u9879\u76ee\u8bc1\u636e\u4e2d\u8bc6\u522b\u51fa\u5e38\u89c1\u95ee\u9898\u3002",
            "No usage patterns were identified from the project evidence.":
                "\u672a\u4ece\u9879\u76ee\u8bc1\u636e\u4e2d\u8bc6\u522b\u51fa\u4f7f\u7528\u6a21\u5f0f\u3002",
            "No platform-specific notes were identified from the project evidence.":
                "\u672a\u4ece\u9879\u76ee\u8bc1\u636e\u4e2d\u8bc6\u522b\u51fa\u5e73\u53f0\u76f8\u5173\u8bf4\u660e\u3002",
            "Platform": "\u5e73\u53f0",
            "Usage Examples": "\u4f7f\u7528\u793a\u4f8b",
            "Documentation Navigation": "\u6587\u6863\u5bfc\u822a",
            "This documentation focuses on user-visible behavior. Internal architecture and source layout are intentionally omitted.":
                "\u672c\u6587\u6863\u53ea\u5173\u6ce8\u7528\u6237\u53ef\u76f4\u63a5\u770b\u5230\u6216\u64cd\u4f5c\u7684\u884c\u4e3a\uff0c\u6709\u610f\u7701\u7565\u5185\u90e8\u67b6\u6784\u4e0e\u6e90\u7801\u76ee\u5f55\u5e03\u5c40\u3002",
            "Only user-facing configuration files are listed here. Build and packaging metadata are intentionally omitted.":
                "\u8fd9\u91cc\u53ea\u5217\u51fa\u9762\u5411\u7528\u6237\u7684\u914d\u7f6e\u6587\u4ef6\uff0c\u6784\u5efa\u4e0e\u6253\u5305\u5143\u6570\u636e\u5df2\u88ab\u6709\u610f\u7701\u7565\u3002",
        },
        "ja": {
            "Configuration file": "\u8a2d\u5b9a\u30d5\u30a1\u30a4\u30eb",
            "Expected output": "\u671f\u5f85\u3055\u308c\u308b\u51fa\u529b",
            "Key": "\u30ad\u30fc",
            "No specific prerequisites were identified from the project evidence.":
                "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306e\u8a3c\u62e0\u304b\u3089\u7279\u5b9a\u306e\u524d\u63d0\u6761\u4ef6\u306f\u78ba\u8a8d\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No configuration items were identified from the project evidence.":
                "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306e\u8a3c\u62e0\u304b\u3089\u8a2d\u5b9a\u9805\u76ee\u306f\u78ba\u8a8d\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No frequently asked questions were identified. Check the project repository for community discussions.":
                "\u3088\u304f\u3042\u308b\u8cea\u554f\u306f\u78ba\u8a8d\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002\u30b3\u30df\u30e5\u30cb\u30c6\u30a3\u306e\u8b70\u8ad6\u306b\u3064\u3044\u3066\u306f\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u30ea\u30dd\u30b8\u30c8\u30ea\u3092\u3054\u78ba\u8a8d\u304f\u3060\u3055\u3044\u3002",
            "No common issues were identified from the project evidence.":
                "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306e\u8a3c\u62e0\u304b\u3089\u4e00\u822c\u7684\u306a\u554f\u984c\u306f\u78ba\u8a8d\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No usage patterns were identified from the project evidence.":
                "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306e\u8a3c\u62e0\u304b\u3089\u4f7f\u7528\u30d1\u30bf\u30fc\u30f3\u306f\u78ba\u8a8d\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "No platform-specific notes were identified from the project evidence.":
                "\u30d7\u30ed\u30b8\u30a7\u30af\u30c8\u306e\u8a3c\u62e0\u304b\u3089\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0\u56fa\u6709\u306e\u6ce8\u610f\u4e8b\u9805\u306f\u78ba\u8a8d\u3055\u308c\u307e\u305b\u3093\u3067\u3057\u305f\u3002",
            "Platform": "\u30d7\u30e9\u30c3\u30c8\u30d5\u30a9\u30fc\u30e0",
            "Usage Examples": "\u4f7f\u7528\u4f8b",
            "Documentation Navigation": "\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\u30ca\u30d3\u30b2\u30fc\u30b7\u30e7\u30f3",
            "This documentation focuses on user-visible behavior. Internal architecture and source layout are intentionally omitted.":
                "\u3053\u306e\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\u306f\u30e6\u30fc\u30b6\u30fc\u304c\u76f4\u63a5\u78ba\u8a8d\u3067\u304d\u308b\u632f\u308b\u821e\u3044\u306b\u7126\u70b9\u3092\u5f53\u3066\u3066\u304a\u308a\u3001\u5185\u90e8\u30a2\u30fc\u30ad\u30c6\u30af\u30c1\u30e3\u3084\u30bd\u30fc\u30b9\u69cb\u6210\u306f\u610f\u56f3\u7684\u306b\u7701\u7565\u3057\u3066\u3044\u307e\u3059\u3002",
            "Only user-facing configuration files are listed here. Build and packaging metadata are intentionally omitted.":
                "\u3053\u3053\u3067\u306f\u30e6\u30fc\u30b6\u30fc\u5411\u3051\u306e\u8a2d\u5b9a\u30d5\u30a1\u30a4\u30eb\u306e\u307f\u3092\u4e00\u89a7\u3057\u3066\u304a\u308a\u3001\u30d3\u30eb\u30c9\u3084\u30d1\u30c3\u30b1\u30fc\u30b8\u30f3\u30b0\u306e\u30e1\u30bf\u30c7\u30fc\u30bf\u306f\u610f\u56f3\u7684\u306b\u9664\u5916\u3057\u3066\u3044\u307e\u3059\u3002",
        },
    }

    @classmethod
    def _uncertainty(cls, profile: LanguageProfile, english: str) -> str:
        lang_map = cls._SIMPLE_TRANSLATIONS.get(profile.code, {})
        return lang_map.get(english, english)

    @classmethod
    def _localize(cls, profile: LanguageProfile, english: str) -> str:
        lang_map = cls._SIMPLE_TRANSLATIONS.get(profile.code, {})
        return lang_map.get(english, english)
