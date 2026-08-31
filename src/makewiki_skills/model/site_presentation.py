"""LLM-authored Site Presentation Plan for the static-site compiler.

The :class:`SitePresentationPlan` is the SINGLE authoritative statement of the
site's Information Architecture (IA) and visual direction. It is authored by
the Main Agent / Site Designer LLM from the :class:`SemanticModel` and the
generated document collection, and it is the ONLY thing the mechanical
:class:`~makewiki_skills.renderer.site_compiler.SiteCompiler` is allowed to
read to decide navigation, page roles, ordering and hierarchy.

This is a hard Cognitive-Authority-Boundary rule: Python never infers IA from
filenames or keywords (no Overview / Getting Started / FAQ / Deployment /
nav-group / ordering / hierarchy heuristics). Python renders exactly what this
plan states. When no plan exists, the SiteCompiler refuses to fabricate one —
site build enters an ``unavailable`` / ``pending`` state rather than guessing,
and the Main Agent's authority to author the plan is preserved.

The plan is deliberately kept free of prose content: it references documents by
stable ``document_id`` and the compiler resolves the localized Markdown content
from the wiki tree mechanically. Every field here is LLM-owned; Python only
validates the schema, resolves document files, and renders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

#: Forbid unknown keys so a hand-authored plan with a typo'd field fails loudly
#: at load time instead of being silently dropped (mirrors config strictness).
_PLAN_CONFIG = ConfigDict(extra="forbid")

#: The site's visual presentation preferences. LLM-authored direction; the
#: compiler renders it mechanically.
ThemeMode = Literal["auto", "light", "dark"]


class SiteVisualPreferences(BaseModel):
    """LLM-authored visual direction for the site.

    Carries presentation preferences only — no page semantics. ``theme`` and
    ``include_search`` are mechanical rendering switches; ``accent_color`` and
    ``brand_label`` are cosmetic direction the renderer applies verbatim.
    """

    model_config = _PLAN_CONFIG

    theme: ThemeMode = "auto"
    include_search: bool = True
    accent_color: str | None = None
    brand_label: str = "MakeWiki"


class SiteNavItem(BaseModel):
    """One page entry in the site navigation.

    Each item is the LLM's decision of *where* a document lives in the IA: its
    stable ``document_id`` (a relative path / slug with no language suffix),
    its URL ``route``, its localized ``title``(s), its ``nav_group`` label, and
    its ``ordering`` within that group. ``children`` express page hierarchy
    (nesting). Python resolves the actual localized Markdown content for
    ``document_id`` mechanically and renders this structure verbatim — it never
    derives any of these fields from the filename or its keywords.
    """

    model_config = _PLAN_CONFIG

    #: Stable document id: the relative path (no language suffix) of the source
    #: file, e.g. ``"README"`` or ``"usage/deploy"``. The compiler resolves the
    #: localized Markdown from this.
    document_id: str
    #: URL route, e.g. ``"/"`` or ``"/deployment"``. Rendered as-is.
    route: str
    #: Default display title. Overridden per-language by :attr:`titles` when present.
    title: str
    #: Per-language localized display titles, keyed by language code (e.g. ``en``,
    #: ``zh-CN``). When a language code is present here, it wins over ``title`` for
    #: that language's rendering; otherwise ``title`` is used mechanically.
    titles: dict[str, str] = Field(default_factory=dict)
    #: Navigation group label the item is listed under (e.g. "Getting Started").
    nav_group: str
    #: Sort position within ``nav_group`` (ascending). Decided by the LLM, never
    #: inferred from the filename.
    ordering: int = 0
    #: Child pages for hierarchy / nesting (page level). Empty for a leaf page.
    children: list[SiteNavItem] = Field(default_factory=list)


class SitePresentationPlan(BaseModel):
    """The LLM-authored, compiler-consumed site plan.

    Field-by-field ownership (all LLM-authored; Python only reads and renders):

    * ``project_title`` / ``project_description`` — site-level identity, authored
      by the Main Agent from the SemanticModel's ``identity``.
    * ``navigation`` — the ordered, grouped, hierarchical page structure. This is
      the ONLY source of site navigation; the compiler renders it verbatim.
    * ``languages`` / ``default_language`` — the set of languages (and the
      default) to render; the language switcher is built from ``languages``.
    * ``visual`` — :class:`SiteVisualPreferences` visual direction.
    """

    model_config = _PLAN_CONFIG

    project_title: str = "Project Documentation"
    project_description: str = ""
    navigation: list[SiteNavItem] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["en"])
    default_language: str = "en"
    visual: SiteVisualPreferences = Field(default_factory=SiteVisualPreferences)

    def nav_item_by_id(self, document_id: str) -> SiteNavItem | None:
        """Return the plan's nav item for ``document_id`` at any depth, or None.

        Recurses through ``children`` without a depth limit, so an item nested
        deeper than two levels is still found. This is a pure lookup by the
        stable ``document_id`` the LLM authored: it never infers or classifies
        IA, never invents a nav item for an unknown document (returns ``None``),
        and never derives structure from filenames or keywords.
        """

        def _find(items: list[SiteNavItem]) -> SiteNavItem | None:
            for item in items:
                if item.document_id == document_id:
                    return item
                found = _find(item.children)
                if found is not None:
                    return found
            return None

        return _find(self.navigation)


def load_site_presentation(path: Path | str) -> SitePresentationPlan:
    """Load a SitePresentationPlan from a ``.json`` or ``.yaml`` file.

    The plan is an LLM-authored artifact (authored by the Main Agent / Site
    Designer from the SemanticModel and the document collection), consumed here
    by the mechanical plane. ``extra="forbid"`` means an unknown key in the file
    fails loudly rather than being silently dropped.
    """
    plan_path = Path(path)
    raw = plan_path.read_text(encoding="utf-8")
    if plan_path.suffix.lower() in (".yaml", ".yml"):
        data = yaml.safe_load(raw) or {}
    else:
        data = json.loads(raw)
    return SitePresentationPlan.model_validate(data)
