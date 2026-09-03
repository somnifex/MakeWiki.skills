"""Static Wiki Website Compiler (plan-driven, mechanical renderer).

Compiles generated Markdown wiki documentation into an offline, zero-dependency,
responsive static website with multilingual switcher, dark/light theme, search,
a per-page table of contents, and mobile navigation.

The compiler is a PURE MECHANICAL renderer. It consumes an LLM-authored
:class:`~makewiki_skills.model.site_presentation.SitePresentationPlan` that
declares the site's Information Architecture (navigation groups, page order,
routes, hierarchy, localized titles) and visual direction, and renders exactly
that plan. It performs NO semantic page classification:

* It never infers a page role, navigation group, ordering, or hierarchy from a
  filename or keyword.
* It locates each document purely by the plan's stable ``document_id`` and
  resolves the localized Markdown content mechanically.
* Markdown is pre-rendered to HTML at build time by ``markdown_render`` using
  ``markdown-it-py`` (a mature CommonMark implementation); the browser only
  injects the finished HTML, so no client-side Markdown parsing exists.
* Without a plan it refuses to compile — it does NOT fabricate an IA — so a
  missing plan leaves site build in an ``unavailable``/``pending`` state that
  never blocks the Main Agent's cognitive work.

This is the Cognitive Authority Boundary for the site: the Main Agent / Site
Designer LLM authorises the plan; Python only packages it.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.site_presentation import (
    SiteNavItem,
    SitePresentationPlan,
)
from makewiki_skills.renderer.markdown_render import render_markdown_document


class SitePlanRequiredError(RuntimeError):
    """Raised when the compiler is asked to build without a presentation plan.

    The compiler refuses to invent an Information Architecture. A missing plan
    is an ``unavailable`` outcome, not a license to classify filenames.
    """


class SiteCompiler:
    """Compiles a plan + a directory of makewiki Markdown files into a site.

    ``plan`` may be supplied at construction or per-``compile`` call. A compile
    without a plan raises :class:`SitePlanRequiredError`.
    """

    def __init__(self, plan: SitePresentationPlan | None = None) -> None:
        self.plan = plan

    def compile(
        self,
        makewiki_dir: Path,
        output_dir: Path | None = None,
        plan: SitePresentationPlan | None = None,
    ) -> list[str]:
        """Compile plan-driven site into output_dir/site."""
        resolved_plan = plan or self.plan
        if resolved_plan is None:
            raise SitePlanRequiredError(
                "No SitePresentationPlan provided. The Main Agent must author "
                "a SitePresentationPlan (the single IA authority) before a site "
                "can be compiled; a build without a plan never fabricates an "
                "Information Architecture from filenames."
            )
        if not resolved_plan.navigation:
            raise SitePlanRequiredError(
                "SitePresentationPlan has an empty navigation. The Main Agent "
                "must declare at least the page structure the site renders."
            )

        makewiki_dir = Path(makewiki_dir).resolve()
        if not makewiki_dir.is_dir():
            raise ValueError(f"MakeWiki directory does not exist: {makewiki_dir}")

        if output_dir is None:
            site_dir = makewiki_dir / "site"
        else:
            site_dir = Path(output_dir).resolve()

        site_dir.mkdir(parents=True, exist_ok=True)

        content_by_lang = self._discover_content(makewiki_dir, resolved_plan)
        html_content = self._render_spa_html(content_by_lang, resolved_plan)

        index_file = site_dir / "index.html"
        index_file.write_text(html_content, encoding="utf-8")

        return [str(index_file)]

    @staticmethod
    def _lang_document_path(makewiki_dir: Path, document_id: str, lang: str) -> Path:
        """Mechanical path resolution for a plan document_id + language.

        Follows the markdown naming convention: the ``en`` content is the plain
        ``<document_id>.md`` while every other language is ``<document_id>.<lang>
        .md``. ``document_id`` IS the relative path from the wiki root (e.g.
        ``"usage/deploy"`` resolves to ``usage/deploy.md``). No filename/keyword
        semantics are interpreted here — the id names the file verbatim.
        """
        suffix = "" if lang == "en" else f".{lang}"
        return makewiki_dir / f"{document_id}{suffix}.md"

    @staticmethod
    def _extract_h1(content_md: str) -> str | None:
        """Mechanically pull the first ``# H1`` from a document, if any."""
        line = next(
            (ln for ln in content_md.splitlines() if ln.startswith("# ")),
            None,
        )
        return line[2:].strip() if line else None

    @staticmethod
    def _flatten_nav_items(items: list[SiteNavItem]) -> list[SiteNavItem]:
        """Flatten root + child nav items into one list (site nav never nests
        beyond two levels)."""
        flat: list[SiteNavItem] = []
        for item in items:
            flat.append(item)
            flat.extend(item.children)
        return flat

    def _discover_content(
        self, makewiki_dir: Path, plan: SitePresentationPlan
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """Mechanically resolve each plan-referenced document to pre-rendered HTML.

        Returns ``{ lang: { document_id: {"html": ..., "title": ...} } }``.
        The document set is EXACTLY the plan's navigation — Python never adds
        documents, groups, or ordering of its own. A document missing for a
        given language is omitted from that language (mechanical absence); a
        plan reference with no file at all is a plan error the renderer surfaces.

        Internal ``.md`` links inside a document are resolved to SPA routes via
        ``route_map`` built from the plan's navigation.
        """
        content_by_lang: dict[str, dict[str, dict[str, Any]]] = {
            lang: {} for lang in plan.languages
        }

        # Resolve root + child nav items; ordering/grouping come from the plan.
        nav_items = self._flatten_nav_items(plan.navigation)
        route_map = {item.document_id: item.route for item in nav_items}

        for lang in plan.languages:
            for item in nav_items:
                path = self._lang_document_path(makewiki_dir, item.document_id, lang)
                if not path.is_file():
                    # Recorded so effective languages can be computed; not an
                    # error the renderer should fail on (a doc may be absent for
                    # one language while present for another).
                    continue
                content_md = path.read_text(encoding="utf-8", errors="replace")
                content_by_lang[lang][item.document_id] = {
                    "html": render_markdown_document(content_md, route_map=route_map),
                    "title": self._extract_h1(content_md) or item.title,
                }

        return content_by_lang

    def _render_spa_html(
        self,
        content_by_lang: dict[str, dict[str, dict[str, Any]]],
        plan: SitePresentationPlan,
    ) -> str:
        """Render the single-file SPA from the plan's IA + resolved content."""

        def _nav_item_dict(item: SiteNavItem) -> dict[str, Any]:
            return {
                "id": item.document_id,
                "route": item.route,
                "title": item.title,
                "titles": item.titles,
                "group": item.nav_group,
                "order": item.ordering,
                "children": [_nav_item_dict(child) for child in item.children],
            }

        # Only languages that actually resolved at least one document are listed
        # in the switcher (a language with zero content cannot render).
        languages = [lang for lang in plan.languages if content_by_lang.get(lang)] or [
            plan.default_language
        ]

        site_config: dict[str, Any] = {
            "projectTitle": plan.project_title,
            "projectDescription": plan.project_description,
            "defaultLang": plan.default_language,
            "languages": languages,
            "visual": {
                "theme": plan.visual.theme,
                "include_search": plan.visual.include_search,
                "accentColor": plan.visual.accent_color,
                "brandLabel": plan.visual.brand_label,
            },
        }
        site_nav: list[dict[str, Any]] = [_nav_item_dict(item) for item in plan.navigation]

        # Pre-rendered HTML keyed by lang -> document_id, plus a per-language
        # ordered index of which documents actually resolved (drives the
        # cross-language fallback so a missing translation is never silent).
        docs_json_obj: dict[str, dict[str, str]] = {}
        docs_index_obj: dict[str, list[str]] = {}
        for lang, docs in content_by_lang.items():
            docs_json_obj[lang] = {doc_id: entry["html"] for doc_id, entry in docs.items()}
            docs_index_obj[lang] = list(docs.keys())

        # Native language names for the switcher (falls back to the code).
        LanguageRegistry.load_builtins()
        lang_names: dict[str, str] = {}
        for code in plan.languages:
            try:
                lang_names[code] = LanguageRegistry.get(code).native_name
            except Exception:
                lang_names[code] = code

        config_json = json.dumps(site_config, ensure_ascii=False).replace("<", "\\u003c")
        nav_json = json.dumps(site_nav, ensure_ascii=False).replace("<", "\\u003c")
        docs_json = json.dumps(docs_json_obj, ensure_ascii=False).replace("<", "\\u003c")
        docs_index_json = json.dumps(docs_index_obj, ensure_ascii=False).replace("<", "\\u003c")
        lang_names_json = json.dumps(lang_names, ensure_ascii=False).replace("<", "\\u003c")

        search_box_html = _SEARCH_BOX_HTML if plan.visual.include_search else ""
        initial_lang = html.escape(plan.default_language, quote=True)

        return f"""<!DOCTYPE html>
<html lang="{initial_lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(plan.project_title)} - MakeWiki</title>
  <style>
{_SPA_CSS}
  </style>
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <header>
    <button class="hamburger" id="hamburger" aria-controls="sidebar" aria-expanded="false" aria-label="Toggle navigation menu">
      <svg class="icon" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
    </button>
    <a href="#/" onclick="navigateTo(siteConfig.defaultLang, '/', true); return false;" class="brand">
      <span class="brand-label">{html.escape(plan.visual.brand_label)}</span>
      <span class="badge">Offline Docs</span>
    </a>
    <div class="nav-actions">
      {search_box_html}
      <select id="langSelect" aria-label="Choose language"></select>
      <button class="theme-btn" id="themeToggle" aria-label="Toggle color theme">
        <svg class="icon-icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
      </button>
    </div>
  </header>

  <div class="layout">
    <nav id="sidebar" aria-label="Page navigation"></nav>
    <div class="overlay" id="overlay" hidden></div>
    <main id="content">
      <div id="docViewer"></div>
      <aside id="tocPanel" aria-label="On this page"></aside>
    </main>
  </div>
  <footer class="footer-note">
    <span>Generated by <strong>MakeWiki.skills</strong></span>
    <span>Zero-Dependency Static Wiki</span>
  </footer>

  <script>
    const siteConfig = {config_json};
    const siteNav = {nav_json};
    const docsContent = {docs_json};
    const docsIndex = {docs_index_json};
    const langNames = {lang_names_json};

{_SPA_JS}
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Static template bodies. These are kept OUT of f-strings so braces and `${}`
# markers in the CSS/JS never need escaping: a punctuation bug in a template
# cannot corrupt a document. Only the JSON payloads above are injected via the
# small head f-string.
# ---------------------------------------------------------------------------

_SEARCH_BOX_HTML = """<button type="button" class="search-trigger" id="searchTrigger"
        aria-label="Search documentation" aria-haspopup="dialog" aria-controls="searchDialog">
      <svg class="icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      <span class="search-word">Search</span>
      <span class="search-kbd">Ctrl K</span>
    </button>
    <dialog id="searchDialog" class="search-dialog" aria-label="Search documentation">
      <div class="search-dialog-head">
        <svg class="icon" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><line x1="16.5" y1="16.5" x2="21" y2="21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        <input type="text" id="searchInput" class="search-input" placeholder="Search docs…  (Esc to close)"
               aria-label="Search documentation" role="combobox" aria-expanded="false"
               aria-controls="searchPanel" aria-autocomplete="list" />
      </div>
      <div id="searchPanel" class="search-panel" role="listbox" aria-live="polite"></div>
    </dialog>"""

_SPA_CSS = """
    /* ====================================================================
       Design tokens. One semantic name per value, shared by light and dark
       (each theme assigns its own values to the SAME names, so no component
       ever branches on theme or reaches for its own hex). The renderer binds
       plan.visual.accent_color into --color-accent (+ derived hover/subtle/
       contrast); when absent the built-in accent below applies.
       ==================================================================== */
    :root {
      color-scheme: light;
      /* color */
      --color-bg: #ffffff;
      --color-surface: #f8fafc;
      --color-sidebar: #f1f5f9;
      --color-border: #e2e8f0;
      --color-text: #0f172a;
      --color-muted: #475569;
      --color-faint: #64748b;
      --color-accent: #2563eb;
      --color-accent-hover: #1d4ed8;
      --color-accent-subtle: #eff6ff;
      --color-accent-contrast: #ffffff;
      --color-code-bg: #1e293b;
      --color-code-text: #f8fafc;
      --color-code-inline-bg: #f1f5f9;
      --color-code-inline-border: #cbd5e1;
      --color-code-inline-text: #be185d;
      --color-callout-note-bg: #eff6ff;
      --color-callout-note-border: #3b82f6;
      --color-callout-warn-bg: #fffbeb;
      --color-callout-warn-border: #f59e0b;
      --color-callout-tip-bg: #f0fdf4;
      --color-callout-tip-border: #22c55e;
      --color-callout-danger-bg: #fef2f2;
      --color-callout-danger-border: #ef4444;
      --color-overlay: rgba(15, 23, 42, 0.45);
      /* typography */
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "SF Mono", monospace;
      --text-xs: 0.75rem;
      --text-sm: 0.85rem;
      --text-base: 1rem;
      --text-lg: 1.05rem;
      --text-xl: 1.2rem;
      --text-2xl: 1.5rem;
      --text-3xl: 2rem;
      --text-mono: 0.875rem;
      --line-body: 1.6;
      --line-cjk: 1.7;
      /* spacing (4px base) */
      --space-1: 0.25rem;
      --space-2: 0.5rem;
      --space-3: 0.75rem;
      --space-4: 1rem;
      --space-6: 1.5rem;
      --space-8: 2rem;
      --space-10: 2.5rem;
      --space-14: 3.5rem;
      /* layout */
      --content-width: 820px;
      --layout-max: 1280px;
      --sidebar-width: 280px;
      --toc-width: 240px;
      --header-height: 56px;
      --main-gutter: clamp(1.25rem, 5vw, 3rem);
      /* radius */
      --radius-sm: 4px;
      --radius-md: 6px;
      --radius-lg: 8px;
      --radius-full: 9999px;
      /* elevation + stacking */
      --shadow-dropdown: 0 10px 30px rgba(0, 0, 0, 0.15);
      --z-header: 50;
      --z-drawer: 45;
      --z-modal: 100;
    }
    [data-theme="dark"] {
      color-scheme: dark;
      --color-bg: #0f172a;
      --color-surface: #1e293b;
      --color-sidebar: #131d31;
      --color-border: #334155;
      --color-text: #f8fafc;
      --color-muted: #cbd5e1;
      --color-faint: #94a3b8;
      --color-accent: #38bdf8;
      --color-accent-hover: #0ea5e9;
      --color-accent-subtle: #1e3a5f;
      --color-accent-contrast: #082f49;
      --color-code-bg: #0b1120;
      --color-code-text: #e2e8f0;
      --color-code-inline-bg: #1e293b;
      --color-code-inline-border: #334155;
      --color-code-inline-text: #f0abfc;
      --color-callout-note-bg: #172554;
      --color-callout-note-border: #38bdf8;
      --color-callout-warn-bg: #451a03;
      --color-callout-warn-border: #f59e0b;
      --color-callout-tip-bg: #052e16;
      --color-callout-tip-border: #22c55e;
      --color-callout-danger-bg: #450a0a;
      --color-callout-danger-border: #ef4444;
      --color-overlay: rgba(0, 0, 0, 0.55);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: var(--font-sans);
      background: var(--color-bg);
      color: var(--color-text);
      line-height: var(--line-body);
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }
    .skip-link {
      position: absolute;
      left: -9999px;
      top: 0;
      background: var(--color-accent);
      color: var(--color-accent-contrast);
      padding: var(--space-2) var(--space-4);
      z-index: 200;
      border-radius: 0 0 var(--radius-md) 0;
    }
    .skip-link:focus { left: 0; }

    /* --- header: compact toolbar with a designed width budget --- */
    header {
      height: var(--header-height);
      background: var(--color-surface);
      border-bottom: 1px solid var(--color-border);
      display: flex;
      align-items: center;
      gap: var(--space-4);
      padding: 0 var(--space-4);
      position: sticky;
      top: 0;
      z-index: var(--z-header);
    }
    header > * { flex-shrink: 1; min-width: 0; }
    .hamburger {
      display: none;
      flex-shrink: 0;
      min-width: 44px;
      min-height: 44px;
      background: transparent;
      border: none;
      border-radius: var(--radius-md);
      color: var(--color-text);
      cursor: pointer;
      line-height: 1;
      align-items: center;
      justify-content: center;
      padding: 0;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      font-weight: 700;
      font-size: 1.05rem;
      color: var(--color-text);
      text-decoration: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
    }
    .brand .brand-label { overflow: hidden; text-overflow: ellipsis; }
    .badge {
      background: var(--color-accent);
      color: var(--color-accent-contrast);
      font-size: var(--text-xs);
      padding: 2px 8px;
      border-radius: var(--radius-full);
      font-weight: 600;
      flex-shrink: 0;
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      flex-shrink: 0;
    }
    .search-trigger {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      height: 34px;
      padding: 0 var(--space-3);
      border-radius: var(--radius-md);
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      color: var(--color-faint);
      font-family: var(--font-sans);
      font-size: var(--text-sm);
      cursor: pointer;
      width: 200px;
      justify-content: flex-start;
    }
    .search-trigger .search-word { flex: 1; text-align: left; }
    .search-trigger .search-kbd {
      font-family: var(--font-mono);
      font-size: 0.7rem;
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 1px 5px;
      color: var(--color-faint);
      white-space: nowrap;
    }
    .search-trigger:hover { border-color: var(--color-accent); color: var(--color-text); }
    .search-trigger .icon { flex-shrink: 0; }

    select, button.theme-btn {
      flex-shrink: 0;
      height: 34px;
      padding: 0 var(--space-3);
      border-radius: var(--radius-md);
      border: 1px solid var(--color-border);
      background: var(--color-bg);
      color: var(--color-text);
      cursor: pointer;
      font-size: var(--text-sm);
      font-family: var(--font-sans);
    }
    button.theme-btn {
      min-width: 44px;
      min-height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      color: var(--color-muted);
    }
    button.theme-btn:hover { color: var(--color-text); border-color: var(--color-accent); }
    .icon, .icon-icon { display: block; }

    /* --- search dialog --- */
    .search-dialog {
      border: none;
      padding: 0;
      border-radius: var(--radius-lg);
      background: var(--color-bg);
      color: var(--color-text);
      width: min(640px, 92vw);
      box-shadow: var(--shadow-dropdown);
      z-index: var(--z-modal);
    }
    .search-dialog::backdrop { background: var(--color-overlay); }
    .search-dialog-head {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-3) var(--space-4);
      border-bottom: 1px solid var(--color-border);
      color: var(--color-faint);
    }
    .search-dialog-head .search-input {
      flex: 1;
      min-width: 0;
      border: none;
      outline: none;
      background: transparent;
      color: var(--color-text);
      font-size: var(--text-lg);
      font-family: var(--font-sans);
    }
    .search-panel {
      max-height: 60vh;
      overflow-y: auto;
      padding: var(--space-1);
    }
    .search-result {
      display: block;
      padding: var(--space-3) var(--space-3);
      cursor: pointer;
      border-radius: var(--radius-md);
      text-decoration: none;
    }
    .search-result.active, .search-result:hover { background: var(--color-accent-subtle); }
    .search-result[aria-selected="true"] { background: var(--color-accent-subtle); }
    .search-result-title { font-weight: 600; color: var(--color-text); }
    .search-result-title em { color: var(--color-accent); font-style: normal; }
    .search-result-snippet { font-size: var(--text-sm); color: var(--color-muted); }
    .search-empty { padding: var(--space-4); color: var(--color-muted); font-size: var(--text-sm); }

    /* --- three-column layout --- */
    .layout { display: flex; flex: 1; min-height: 0; }
    #sidebar {
      width: var(--sidebar-width);
      background: var(--color-sidebar);
      border-right: 1px solid var(--color-border);
      padding: var(--space-6) var(--space-4);
      height: calc(100vh - var(--header-height));
      position: sticky;
      top: var(--header-height);
      overflow-y: auto;
      flex-shrink: 0;
    }
    .nav-group { margin-bottom: var(--space-6); }
    .nav-group-title {
      font-size: var(--text-xs);
      text-transform: uppercase;
      font-weight: 700;
      color: var(--color-faint);
      margin-bottom: var(--space-2);
      padding-left: var(--space-2);
      letter-spacing: 0.05em;
    }
    .nav-item {
      display: flex;
      align-items: center;
      padding: var(--space-2) var(--space-3);
      min-height: 44px; /* >= WCAG 2.5.5 touch target */
      color: var(--color-muted);
      text-decoration: none;
      border-radius: var(--radius-md);
      font-size: 0.9rem;
      margin-bottom: 2px;
      transition: background 0.15s, color 0.15s;
      cursor: pointer;
    }
    .nav-item.child { padding-left: var(--space-6); font-size: var(--text-sm); }
    .nav-item:hover { background: var(--color-border); color: var(--color-text); }
    .nav-item.active { background: var(--color-accent); color: var(--color-accent-contrast); font-weight: 600; }
    main {
      flex: 1;
      min-width: 0;
      padding: var(--space-8) var(--main-gutter);
      max-width: var(--layout-max);
      margin: 0 auto;
      display: flex;
      gap: var(--space-8);
      width: 100%;
    }
    #docViewer { flex: 1; min-width: 0; max-width: var(--content-width); overflow-x: auto; }
    #tocPanel {
      width: var(--toc-width);
      flex-shrink: 0;
      position: sticky;
      top: calc(var(--header-height) + var(--space-6));
      height: fit-content;
      align-self: flex-start;
      font-size: var(--text-sm);
      border-left: 1px solid var(--color-border);
      padding-left: var(--space-4);
    }
    #tocPanel h4 { text-transform: uppercase; font-size: var(--text-xs); color: var(--color-faint); letter-spacing: 0.05em; margin-bottom: var(--space-2); }
    #tocPanel a { display: block; color: var(--color-muted); text-decoration: none; padding: var(--space-1) 0; border-left: 2px solid transparent; padding-left: var(--space-2); }
    #tocPanel a:hover { color: var(--color-text); }
    #tocPanel a.active { color: var(--color-accent); border-left-color: var(--color-accent); font-weight: 600; }
    #tocPanel a.lvl-3 { padding-left: var(--space-6); font-size: var(--text-sm); }

    /* --- document typography scale --- */
    #docViewer h1 { font-size: var(--text-3xl); font-weight: 700; line-height: 1.25; margin-bottom: var(--space-4); color: var(--color-text); }
    #docViewer h2 { font-size: var(--text-2xl); font-weight: 650; line-height: 1.3; margin-top: var(--space-8); margin-bottom: var(--space-3); border-bottom: 1px solid var(--color-border); padding-bottom: 0.3rem; color: var(--color-text); }
    #docViewer h3 { font-size: var(--text-xl); font-weight: 650; line-height: 1.35; margin-top: var(--space-6); margin-bottom: var(--space-2); color: var(--color-text); }
    #docViewer h4 { font-size: var(--text-lg); font-weight: 600; line-height: 1.4; margin-top: var(--space-4); margin-bottom: var(--space-1); color: var(--color-text); }
    #docViewer p {
      margin-bottom: var(--space-4);
      color: var(--color-text);
      font-size: var(--text-lg);
      line-height: var(--line-body);
      max-width: 72ch;
      overflow-wrap: break-word;
    }
    #docViewer ul, #docViewer ol { margin-left: var(--space-6); margin-bottom: var(--space-4); color: var(--color-text); overflow-wrap: break-word; }
    #docViewer ul ul, #docViewer ol ol, #docViewer ul ol, #docViewer ol ul { margin-left: var(--space-6); }
    #docViewer li { margin-bottom: var(--space-2); line-height: var(--line-body); }
    #docViewer p, #docViewer li, #docViewer td { overflow-wrap: break-word; }
    #docViewer :lang(zh-CN) p, #docViewer :lang(zh-CN) li, html[lang="zh-CN"] #docViewer p, html[lang="zh-CN"] #docViewer li {
      line-height: var(--line-cjk);
    }

    /* --- code blocks: fixed header strip (language + copy) on the slab --- */
    #docViewer pre {
      background: var(--color-code-bg);
      color: var(--color-code-text);
      padding: 0;
      border-radius: var(--radius-lg);
      overflow: hidden;
      margin-bottom: var(--space-6);
      position: relative;
      font-family: var(--font-mono);
      font-size: var(--text-mono);
    }
    .code-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: var(--color-surface);
      color: var(--color-faint);
      font-family: var(--font-mono);
      font-size: var(--text-xs);
      padding: var(--space-2) var(--space-3);
      border-bottom: 1px solid var(--color-border);
      border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }
    .code-header .code-lang { text-transform: uppercase; letter-spacing: 0.04em; }
    .code-scroll { overflow-x: auto; padding: var(--space-4); }
    #docViewer pre code { font-family: var(--font-mono); font-size: inherit; }

    /* --- inline code: a neutral chip, NOT the accent (link colour) --- */
    #docViewer code {
      font-family: var(--font-mono);
      font-size: 0.9em;
      background: var(--color-code-inline-bg);
      border: 1px solid var(--color-code-inline-border);
      color: var(--color-code-inline-text);
      padding: 0.1rem 0.35rem;
      border-radius: var(--radius-sm);
    }
    #docViewer pre code { background: transparent; border: none; padding: 0; color: inherit; }

    /* --- links --- */
    #docViewer a { color: var(--color-accent); text-decoration: underline; text-underline-offset: 2px; }
    #docViewer a:hover { text-decoration: underline; color: var(--color-accent-hover); }
    #docViewer a:visited { color: var(--color-accent-hover); }
    .wiki-link { color: var(--color-accent); font-weight: 500; cursor: pointer; text-decoration: underline; text-underline-offset: 2px; }
    .external-link { color: var(--color-accent); font-size: 0.95em; }
    .copy-btn {
      background: var(--color-accent);
      border: none;
      color: var(--color-accent-contrast);
      padding: var(--space-1) var(--space-2);
      border-radius: var(--radius-sm);
      font-size: var(--text-xs);
      font-family: var(--font-sans);
      cursor: pointer;
      min-width: 56px;
      min-height: 44px; /* >= WCAG 2.5.5 touch target */
    }
    .copy-btn:hover { background: var(--color-accent-hover); }

    /* --- tables --- */
    #docViewer table { width: 100%; border-collapse: collapse; margin: var(--space-6) 0; display: block; overflow-x: auto; }
    #docViewer th, #docViewer td { border: 1px solid var(--color-border); padding: var(--space-3) var(--space-3); text-align: left; font-size: var(--text-sm); vertical-align: top; line-height: var(--line-body); }
    #docViewer th { background: var(--color-surface); font-weight: 600; }

    /* --- callouts (note / tip / warning / danger) vs plain blockquote --- */
    #docViewer blockquote {
      border-left: 4px solid var(--color-border);
      background: transparent;
      color: var(--color-muted);
      padding: var(--space-1) var(--space-4);
      margin: var(--space-4) 0;
      font-style: italic;
    }
    #docViewer .callout {
      border-left: 4px solid var(--color-callout-note-border);
      background: var(--color-callout-note-bg);
      padding: var(--space-3) var(--space-4);
      border-radius: 0 var(--radius-md) var(--radius-md) 0;
      margin: var(--space-6) 0;
      font-style: normal;
      color: var(--color-text);
    }
    #docViewer .callout .callout-label {
      display: block;
      font-size: var(--text-xs);
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: var(--space-1);
    }
    #docViewer .callout.note { border-left-color: var(--color-callout-note-border); background: var(--color-callout-note-bg); }
    #docViewer .callout.tip { border-left-color: var(--color-callout-tip-border); background: var(--color-callout-tip-bg); }
    #docViewer .callout.warning { border-left-color: var(--color-callout-warn-border); background: var(--color-callout-warn-bg); }
    #docViewer .callout.danger { border-left-color: var(--color-callout-danger-border); background: var(--color-callout-danger-bg); }
    #docViewer .callout.note .callout-label { color: var(--color-callout-note-border); }
    #docViewer .callout.tip .callout-label { color: var(--color-callout-tip-border); }
    #docViewer .callout.warning .callout-label { color: var(--color-callout-warn-border); }
    #docViewer .callout.danger .callout-label { color: var(--color-callout-danger-border); }
    #docViewer hr { border: 0; border-top: 1px solid var(--color-border); margin: var(--space-8) 0; }
    .fallback-banner {
      background: var(--color-callout-warn-bg);
      border: 1px solid var(--color-callout-warn-border);
      color: var(--color-text);
      padding: var(--space-2) var(--space-4);
      border-radius: var(--radius-md);
      font-size: var(--text-sm);
      margin-bottom: var(--space-6);
    }
    .footer-note {
      margin: 0 auto;
      max-width: var(--layout-max);
      width: 100%;
      padding: var(--space-6) var(--main-gutter) var(--space-8);
      border-top: 1px solid var(--color-border);
      color: var(--color-faint);
      font-size: var(--text-sm);
      display: flex;
      justify-content: space-between;
      gap: var(--space-4);
    }
    .overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: var(--color-overlay);
      z-index: var(--z-drawer);
    }
    :focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
    .nav-item.active:focus-visible, .badge:focus-visible { outline-color: var(--color-accent-contrast); }
    .search-dialog:focus-visible { outline: none; }

    @media (max-width: 1100px) { #tocPanel { display: none; } }

    @media (max-width: 768px) {
      header { padding: 0 var(--space-3); }
      .hamburger { display: flex; }
      .brand .badge { display: none; }
      .search-trigger { width: 44px; padding: 0; justify-content: center; }
      .search-trigger .search-word, .search-trigger .search-kbd { display: none; }
      .search-trigger .icon { width: 20px; height: 20px; }
      .layout { flex-direction: column; }
      #sidebar {
        position: fixed;
        top: var(--header-height);
        left: 0;
        bottom: 0;
        width: var(--sidebar-width);
        height: auto;
        transform: translateX(-100%);
        visibility: hidden;
        transition: transform 0.25s ease, visibility 0.25s;
        z-index: var(--z-drawer);
        box-shadow: 2px 0 8px rgba(0,0,0,0.1);
      }
      #sidebar.open { transform: translateX(0); visibility: visible; }
      .overlay.open { display: block; }
      main { padding: var(--space-6) var(--space-4); flex-direction: column; }
      #docViewer { overflow-x: auto; }
      #docViewer p { max-width: none; }
    }
    @media (max-width: 420px) {
      header { gap: var(--space-2); }
      .brand { font-size: 0.95rem; }
      .nav-actions { gap: var(--space-1); }
      #langSelect { max-width: 64px; padding: 0 var(--space-2); }
    }
"""


# The SPA shell: routing (document routes vs in-page anchors), navigation, the
# document viewer (injecting pre-rendered HTML), search, theme, language, the
# on-page table of contents, the mobile drawer, and code copy.
_SPA_JS = """
    let currentLang = siteConfig.defaultLang;
    let currentRoute = null;

    // --- navigation helpers (nav structure comes ONLY from the plan) ---

    function allNavItems() {
      const out = [];
      siteNav.forEach(group => {
        out.push(group);
        (group.children || []).forEach(c => out.push(c));
      });
      return out;
    }

    function navItemByRoute(route) {
      return allNavItems().find(i => i.route === route) || null;
    }

    function navItemByHome() { return siteNav.length ? siteNav[0] : null; }

    function activeNavItem() {
      if (currentRoute) {
        const byRoute = navItemByRoute(currentRoute);
        if (byRoute) return byRoute;
      }
      return navItemByHome();
    }

    function itemTitle(item, lang) {
      return (item.titles && item.titles[lang]) || item.title;
    }

    function hasContent(item, lang) {
      return !!(docsIndex[lang] && docsIndex[lang].indexOf(item.id) !== -1);
    }

    // Whether this language really has the document, or we must fall back.
    function docAvailable(item, lang) {
      if (hasContent(item, lang)) return true;
      return false;
    }

    function firstRoutableItem(lang) {
      return allNavItems().find(i => hasContent(i, lang)) || null;
    }

    // --- navigation (document routes vs in-page anchors) ---

    function navigateTo(lang, route, updateHash, anchor) {
      if (lang) currentLang = lang;
      if (route !== undefined && route !== null) currentRoute = route;
      else {
        const item = activeNavItem();
        currentRoute = item ? item.route : (firstRoutableItem(currentLang) || {route: '/'}).route;
      }
      if (siteConfig.languages.indexOf(currentLang) === -1) {
        currentLang = siteConfig.defaultLang;
      }
      const targetHash = '#' + (currentRoute.startsWith('/') ? currentRoute : '/' + currentRoute);
      if (updateHash && window.location.hash !== targetHash) {
        window.location.hash = targetHash;
      }
      renderSidebar();
      renderDoc(anchor);
      closeDrawer();
      window.scrollTo({ top: 0 });
    }

    // --- sidebar rendering (painting the plan's IA, verbatim) ---

    function renderSidebar() {
      const sidebar = document.getElementById('sidebar');
      sidebar.innerHTML = '';
      const active = activeNavItem();

      const groups = [];
      const groupIndex = {};
      siteNav.forEach(item => {
        const items = [item].concat(item.children || []);
        items.forEach(ni => {
          let g = groupIndex[ni.group];
          if (g === undefined) {
            g = { name: ni.group, items: [] };
            groupIndex[ni.group] = g;
            groups.push(g);
          }
          g.items.push(ni);
        });
      });

      groups.forEach(g => {
        g.items.sort((a, b) => a.order - b.order);
        const grp = document.createElement('div');
        grp.className = 'nav-group';
        const title = document.createElement('div');
        title.className = 'nav-group-title';
        title.textContent = g.name;
        grp.appendChild(title);
        g.items.forEach(ni => {
          const a = document.createElement('a');
          const isActive = active && ni.route === active.route;
          a.className = 'nav-item' + (ni.parent ? ' child' : '') + (isActive ? ' active' : '');
          a.textContent = itemTitle(ni, currentLang);
          a.href = '#' + ni.route;
          a.setAttribute('data-route', ni.route);
          if (isActive) a.setAttribute('aria-current', 'page');
          a.onclick = (e) => { e.preventDefault(); navigateTo(currentLang, ni.route, true); };
          grp.appendChild(a);
        });
        sidebar.appendChild(grp);
      });

      // Keep the current page in view on long nav so the user never loses their
      // place (the sidebar scrolls independently per its fixed-height overflow).
      const activeEl = sidebar.querySelector('.nav-item.active');
      if (activeEl && activeEl.scrollIntoView) {
        try { activeEl.scrollIntoView({ block: 'nearest' }); } catch (err) { /* never fails init */ }
      }
    }

    // --- language + native names ---

    function getLangLabel(code) {
      return langNames[code] || code;
    }

    function setDocumentLang(lang) {
      document.documentElement.setAttribute('lang', lang);
    }

    function renderLangSelect() {
      const langSelect = document.getElementById('langSelect');
      langSelect.innerHTML = '';
      siteConfig.languages.forEach(lang => {
        const opt = document.createElement('option');
        opt.value = lang;
        opt.textContent = getLangLabel(lang);
        langSelect.appendChild(opt);
      });
      langSelect.value = currentLang;
    }

    // --- theme (auto / light / dark, persisted) ---

    function prefersDark() {
      return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function applyTheme(resolved) {
      const root = document.documentElement;
      if (resolved === 'dark') { root.setAttribute('data-theme', 'dark'); root.style.colorScheme = 'dark'; }
      else { root.setAttribute('data-theme', 'light'); root.style.colorScheme = 'light'; }
      root.setAttribute('data-theme-resolved', resolved);
      // The effective theme drives the contrast text placed on top of the
      // accent chips; recompute it whenever the theme actually changes.
      bindAccent();
    }

    // Bind the plan's chosen accent (and derived hue) into the token layer so a
    // single --color-accent recolors the whole surface. Mechanical and
    // parametric: falls back silently when the plan omits it.
    function bindAccent() {
      const accent = siteConfig.visual && siteConfig.visual.accentColor;
      const root = document.documentElement;
      // Contrast text that sits on top of an accent-filled chip. Derived from
      // the *effective* theme (dark theme -> light text, light theme -> dark
      // text) rather than the accent's own luminance: this is deterministic,
      // keeps the pair high-contrast for any plan-provided hue, and never does
      // perceptual color math in JS. Falls back to the CSS token when needed.
      const effectiveDark = root.getAttribute('data-theme') === 'dark';
      root.style.setProperty('--color-accent-contrast', effectiveDark ? '#f8fafc' : '#0f172a');
      if (!accent) return;
      root.style.setProperty('--color-accent', accent);
      // Derive a hover from the accent by darkening (light theme) or
      // lightening (dark); a naive RGB step toward black/white.
      const r = parseInt(accent.slice(1, 3), 16), g = parseInt(accent.slice(3, 5), 16), b = parseInt(accent.slice(5, 7), 16);
      const step = effectiveDark ? 24 : -24;
      const c = (v) => { const n = Math.max(0, Math.min(255, v + step)); return n.toString(16).padStart(2, '0'); };
      root.style.setProperty('--color-accent-hover', '#' + c(r) + c(g) + c(b));
    }

    function initTheme() {
      const stored = (() => { try { return localStorage.getItem('site-theme'); } catch (e) { return null; } })();
      const pref = stored || siteConfig.visual.theme || 'auto';
      const resolved = pref === 'auto' ? (prefersDark() ? 'dark' : 'light') : pref;
      applyTheme(resolved);
      bindAccent();
      if (pref === 'auto' && window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
          if (((() => { try { return localStorage.getItem('site-theme'); } catch (err) { return null; } })() || siteConfig.visual.theme || 'auto') === 'auto') {
            applyTheme(e.matches ? 'dark' : 'light');
          }
        });
      }
      window.__themePref = pref;
    }

    function toggleTheme() {
      const root = document.documentElement;
      const cur = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const next = cur === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem('site-theme', next); window.__themePref = next; } catch (e) {}
    }

    // --- mobile drawer (off-canvas, with focus trap + restoration) ---

    let drawerLastFocus = null;

    function openDrawer() {
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('overlay');
      const burger = document.getElementById('hamburger');
      // The opener is always the hamburger; track it explicitly because the
      // mousedown default (which would focus it) is prevented, so the live
      // activeElement here is usually the inert body.
      drawerLastFocus = burger;
      sidebar.classList.add('open');
      sidebar.setAttribute('aria-hidden', 'false');
      overlay.hidden = false;
      overlay.classList.add('open');
      burger.setAttribute('aria-expanded', 'true');
      // Inert everything outside the drawer so keyboard users cannot Tab into
      // off-canvas links; move focus into the drawer's first nav link.
      document.getElementById('content') && (document.getElementById('content').inert = true);
      burger.inert = false;
      // Move focus into the drawer's first nav link. The hamburger's mousedown
      // is prevented (see init) so nothing re-asserts focus on the button. The
      // move is deferred past the drawer's visibility/transform transition
      // (~250ms): focusing mid-transition is a silent no-op in Chromium, and
      // only once the drawer is settled is the link reliably focusable.
      const firstLink = sidebar.querySelector('a');
      if (firstLink) setTimeout(() => { firstLink.focus(); }, 280);
    }

    function closeDrawer() {
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('overlay');
      const burger = document.getElementById('hamburger');
      sidebar.classList.remove('open');
      sidebar.setAttribute('aria-hidden', 'true');
      if (overlay) { overlay.hidden = true; overlay.classList.remove('open'); }
      document.getElementById('content') && (document.getElementById('content').inert = false);
      burger.setAttribute('aria-expanded', 'false');
      // Restore focus to whichever control opened the drawer.
      if (drawerLastFocus && drawerLastFocus.focus) drawerLastFocus.focus();
      drawerLastFocus = null;
    }

    // --- document rendering (inject pre-rendered HTML) ---

    function currentDocHtml(item) {
      if (!item) return null;
      const own = docsContent[currentLang] && docsContent[currentLang][item.id];
      if (own !== undefined) return own;
      return null;
    }

    function shouldFallback(item) {
      return currentLang !== siteConfig.defaultLang && !hasContent(item, currentLang) && hasContent(item, siteConfig.defaultLang);
    }

    function renderDoc(anchor) {
      const viewer = document.getElementById('docViewer');
      const item = activeNavItem();
      if (!item) {
        viewer.innerHTML = '<h1>Document Not Found</h1><p>The requested page could not be found.</p><p><a href="#/" onclick="navigateTo(null, \'/\', true); return false;" class="wiki-link">← Return home</a></p>';
        return;
      }
      let html = currentDocHtml(item);
      let fallbackBanner = '';
      if (html === null && shouldFallback(item)) {
        html = docsContent[siteConfig.defaultLang] && docsContent[siteConfig.defaultLang][item.id];
        const nativeName = getLangLabel(siteConfig.defaultLang);
        fallbackBanner = '<div class="fallback-banner">This page is not yet available in ' +
          getLangLabel(currentLang) + '. Showing the ' + nativeName + ' version. ' +
          '<a href="#/" onclick="navigateTo(siteConfig.defaultLang, null, true); return false;">Switch to ' + nativeName + '</a>.</div>';
      }
      if (html === null) {
        viewer.innerHTML = '<h1>Document Not Found</h1><p>The requested page could not be found.</p><p><a href="#/" onclick="navigateTo(null, \'/\', true); return false;" class="wiki-link">← Return home</a></p>';
        return;
      }
      viewer.innerHTML = fallbackBanner + html;
      attachCopyButtons();
      buildToc();
      if (anchor) {
        const el = document.getElementById(anchor);
        if (el) el.scrollIntoView();
      }
    }

    // --- code copy (event-delegated per block, with a fixed header strip) ---

    function attachCopyButtons() {
      const viewer = document.getElementById('docViewer');
      viewer.querySelectorAll('pre').forEach(pre => {
        if (pre.querySelector('.copy-btn')) return;
        const code = pre.querySelector('code');
        const langMatch = code && code.className ? String(code.className).match(/language-([A-Za-z0-9_+-]+)/) : null;
        const lang = langMatch ? langMatch[1] : 'code';
        const header = document.createElement('div');
        header.className = 'code-header';
        const langLabel = document.createElement('span');
        langLabel.className = 'code-lang';
        langLabel.textContent = lang;
        const btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.textContent = 'Copy';
        btn.setAttribute('aria-label', 'Copy code block');
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const c = pre.querySelector('code');
          const text = c ? c.innerText : pre.innerText;
          const done = () => {
            const orig = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = orig, 1500);
          };
          const fallback = () => {
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); } catch (err) {}
            document.body.removeChild(ta);
            done();
          };
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done).catch(fallback);
          } else {
            fallback();
          }
        });
        header.appendChild(langLabel);
        header.appendChild(btn);
        pre.insertBefore(header, pre.firstChild);
        // The code body scrolls horizontally inside the slab, under the strip.
        const scroll = document.createElement('div');
        scroll.className = 'code-scroll';
        if (code) { pre.appendChild(scroll); scroll.appendChild(code); }
      });
    }

    // --- table of contents (H2 / H3) + scrollspy ---

    function buildToc() {
      const panel = document.getElementById('tocPanel');
      panel.innerHTML = '';
      const viewer = document.getElementById('docViewer');
      const heads = Array.prototype.slice.call(viewer.querySelectorAll('h2, h3'));
      if (!heads.length) return;
      const title = document.createElement('h4');
      title.textContent = 'On this page';
      panel.appendChild(title);
      heads.forEach(h => {
        const a = document.createElement('a');
        a.href = '#' + h.id;
        if (h.tagName === 'H3') a.className = 'lvl-3';
        a.textContent = h.textContent;
        a.addEventListener('click', (e) => {
          e.preventDefault();
          h.scrollIntoView({ behavior: 'smooth' });
          history.replaceState(null, '', '#' + window.location.hash.split('#')[1] + '#' + h.id);
        });
        panel.appendChild(a);
      });
    }

    function scrollspy() {
      const panel = document.getElementById('tocPanel');
      const links = panel.querySelectorAll('a');
      if (!links.length) return;
      const heads = Array.prototype.slice.call(document.getElementById('docViewer').querySelectorAll('h2, h3'));
      let currentId = null;
      const pos = window.scrollY + 90;
      heads.forEach(h => { if (h.offsetTop <= pos) currentId = h.id; });
      links.forEach(a => {
        const isActive = a.textContent && currentId && a.getAttribute('href') === '#' + currentId;
        if (isActive) a.classList.add('active');
        else a.classList.remove('active');
      });
    }

    // --- search (title + headings + body, snippet, / and Ctrl/Cmd+K) ---
    // Builds a lightweight index over the pre-rendered HTML at first use.

    let searchIndex = null;

    function textOfHtml(htmlStr) {
      const el = document.createElement('div');
      el.innerHTML = htmlStr;
      return (el.textContent || '').replace(/\\s+/g, ' ').toLowerCase();
    }

    function buildSearchIndex() {
      const index = [];
      allNavItems().forEach(item => {
        const html = docsContent[currentLang] && docsContent[currentLang][item.id];
        if (!html) return;
        index.push({
          id: item.id,
          route: item.route,
          title: itemTitle(item, currentLang),
          titleLower: itemTitle(item, currentLang).toLowerCase(),
          text: textOfHtml(html)
        });
      });
      return index;
    }

    function highlightText(text, q) {
      const i = text.toLowerCase().indexOf(q);
      if (i === -1) return text;
      const start = Math.max(0, i - 40);
      const end = Math.min(text.length, i + q.length + 60);
      return (start > 0 ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : '');
    }

    function escapeText(s) {
      const d = document.createElement('div');
      d.textContent = s;
      return d.innerHTML;
    }

    function renderSearchResults(query, results) {
      const panel = document.getElementById('searchPanel');
      if (!panel) return;
      panel.innerHTML = '';
      if (!query) {
        const hint = document.createElement('div');
        hint.className = 'search-empty';
        hint.textContent = 'Start typing to search page titles, headings, and body text.';
        panel.appendChild(hint);
        return;
      }
      if (!results.length) {
        const empty = document.createElement('div');
        empty.className = 'search-empty';
        empty.textContent = 'No pages match "' + query + '". Try "deploy", "config", or "handler".';
        panel.appendChild(empty);
        return;
      }
      results.forEach(r => {
        const a = document.createElement('a');
        a.className = 'search-result';
        a.href = '#' + r.route;
        a.setAttribute('data-route', r.route);
        a.setAttribute('role', 'option');
        a.setAttribute('aria-selected', 'false');
        const title = document.createElement('div');
        title.className = 'search-result-title';
        const qIdx = r.titleLower.indexOf(query);
        if (qIdx !== -1) {
          title.innerHTML = escapeText(r.title.slice(0, qIdx)) + '<em>' + escapeText(r.title.slice(qIdx, qIdx + query.length)) + '</em>' + escapeText(r.title.slice(qIdx + query.length));
        } else {
          title.textContent = r.title;
        }
        const snip = document.createElement('div');
        snip.className = 'search-result-snippet';
        snip.textContent = highlightText(r.text, query);
        a.appendChild(title);
        a.appendChild(snip);
        a.addEventListener('click', (e) => {
          e.preventDefault();
          closeSearch(true);
          navigateTo(currentLang, r.route, true);
        });
        a.addEventListener('mousemove', () => setActiveResult(a));
        panel.appendChild(a);
      });
    }

    function setActiveResult(el) {
      const panel = document.getElementById('searchPanel');
      const input = document.getElementById('searchInput');
      panel.querySelectorAll('.search-result').forEach((r, i) => {
        const active = r === el;
        r.classList.toggle('active', active);
        r.setAttribute('aria-selected', active ? 'true' : 'false');
        if (active && input) input.setAttribute('aria-activedescendant', r.id || ('sr-' + i));
      });
      if (el && el.scrollIntoView) { try { el.scrollIntoView({ block: 'nearest' }); } catch (err) {} }
    }

    let searchActiveIndex = -1;

    function moveActive(delta) {
      const panel = document.getElementById('searchPanel');
      const items = panel.querySelectorAll('.search-result');
      if (!items.length) return;
      searchActiveIndex = (searchActiveIndex + delta + items.length) % items.length;
      setActiveResult(items[searchActiveIndex]);
    }

    function openSearch() {
      const dialog = document.getElementById('searchDialog');
      const input = document.getElementById('searchInput');
      if (!dialog || !input) return;
      if (!dialog.open) {
        try { dialog.showModal(); } catch (err) { return; }
      }
      // Seeding the panel before opening keeps the empty state announced and
      // visible (not a blank region) for assistive tech on first open.
      renderSearchResults('', []);
      input.focus();
    }

    function closeSearch(restore) {
      const dialog = document.getElementById('searchDialog');
      const input = document.getElementById('searchInput');
      if (dialog && dialog.open) dialog.close();
      if (input) input.value = '';
      if (restore) {
        const trigger = document.getElementById('searchTrigger');
        if (trigger) trigger.focus();
      }
    }

    function handleSearch(e) {
      const query = e.target.value.toLowerCase().trim();
      const input = document.getElementById('searchInput');
      if (input) input.setAttribute('aria-expanded', 'true');
      searchActiveIndex = -1;
      if (!query) { renderSearchResults('', []); return; }
      if (!searchIndex) searchIndex = buildSearchIndex();
      const results = searchIndex.filter(r =>
        r.titleLower.indexOf(query) !== -1 || r.text.indexOf(query) !== -1
      ).slice(0, 12);
      renderSearchResults(query, results);
    }

    // --- wiki-link slug resolution (kept for contract; wiki links render with
    //     resolved routes at build time, so this is a deliberate fallback) ---

    function resolveInternalSlug(target) {
      let clean = target.trim();
      if (clean.startsWith('./')) clean = clean.slice(2);
      const hashIdx = clean.indexOf('#');
      if (hashIdx !== -1) clean = clean.slice(0, hashIdx);
      clean = clean.replace(/\\.([a-z]{2}(?:-[A-Z]{2,4})?)?\\.md$/i, '').replace(/\\.md$/i, '');
      return clean;
    }

    // --- init ---

    function init() {
      initTheme();

      renderLangSelect();
      langSelect.value = currentLang;
      langSelect.addEventListener('change', (e) => {
        setDocumentLang(e.target.value);
        navigateTo(e.target.value, null, true);
      });
      setDocumentLang(currentLang);

      document.getElementById('themeToggle').addEventListener('click', toggleTheme);

      const searchInput = document.getElementById('searchInput');
      const searchTrigger = document.getElementById('searchTrigger');
      const searchDialog = document.getElementById('searchDialog');
      if (searchInput && searchTrigger) {
        searchTrigger.addEventListener('click', openSearch);
        searchInput.addEventListener('input', handleSearch);
        searchInput.addEventListener('keydown', (e) => {
          if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
          else if (e.key === 'ArrowUp') { e.preventDefault(); moveActive(-1); }
          else if (e.key === 'Enter') {
            const active = document.querySelector('#searchPanel .search-result.active');
            const target = active || document.querySelector('#searchPanel .search-result');
            if (target) {
              e.preventDefault();
              closeSearch(true);
              navigateTo(currentLang, target.getAttribute('data-route'), true);
            }
          }
          else if (e.key === 'Escape') closeSearch(true);
        });
        // Native <dialog> gives us focus trapping + ::backdrop for free.
        if (searchDialog) {
          searchDialog.addEventListener('cancel', (e) => { e.preventDefault(); closeSearch(true); });
          // Closing on a backdrop click (the click lands on the dialog itself).
          searchDialog.addEventListener('click', (e) => {
            if (e.target === searchDialog) closeSearch(true);
          });
          searchDialog.addEventListener('close', () => {
            searchInput.value = '';
            if (searchInput) searchInput.setAttribute('aria-expanded', 'false');
            const panel = document.getElementById('searchPanel');
            if (panel) panel.innerHTML = '';
          });
        }
        document.addEventListener('keydown', (e) => {
          if ((e.key === '/' && document.activeElement !== searchInput && !e.metaKey && !e.ctrlKey && !e.altKey) ||
              ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
            e.preventDefault();
            openSearch();
          }
        });
      }

      const burger = document.getElementById('hamburger');
      if (burger) {
        // Don't let the browser focus the hamburger on mousedown: openDrawer
        // moves focus into the drawer and this would race/override it. Keyboard
        // activation (Enter/Space -> click) is unaffected because it fires the
        // click event without a mousedown.
        burger.addEventListener('mousedown', (e) => e.preventDefault());
        burger.addEventListener('click', () => {
          const sidebar = document.getElementById('sidebar');
          if (sidebar.classList.contains('open')) closeDrawer();
          else openDrawer();
        });
      }
      const overlay = document.getElementById('overlay');
      if (overlay) overlay.addEventListener('click', closeDrawer);
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { closeDrawer(); closeSearch(); }
      });

      window.addEventListener('scroll', scrollspy, { passive: true });

      // Route vs anchor namespacing: a decoded hash starting with '/' is a
      // document route; anything else is an in-page heading anchor (the browser
      // scrolls to it, never a navigateTo).
      window.addEventListener('hashchange', () => {
        const v = decodeURIComponent(window.location.hash.slice(1));
        if (v.startsWith('/') || v === '') {
          navigateTo(null, v || '/', false);
        }
      });

      if (window.location.hash && window.location.hash.length > 1) {
        currentRoute = decodeURIComponent(window.location.hash.slice(1));
      } else {
        const first = firstRoutableItem(currentLang);
        currentRoute = first ? first.route : (navItemByHome() || {route: '/'}).route;
      }
      renderSidebar();
      renderDoc();
    }

    window.addEventListener('DOMContentLoaded', init);
"""
