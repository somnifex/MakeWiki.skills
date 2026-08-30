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
    <button class="hamburger" id="hamburger" aria-controls="sidebar" aria-expanded="false" aria-label="Toggle navigation menu">☰</button>
    <a href="#/" onclick="navigateTo(siteConfig.defaultLang, '/', true); return false;" class="brand">
      <span>📚 {html.escape(plan.visual.brand_label)}</span>
      <span class="badge">Offline Docs</span>
    </a>
    <div class="nav-actions">
      {search_box_html}
      <select id="langSelect" aria-label="Choose language"></select>
      <button class="theme-btn" id="themeToggle" aria-label="Toggle color theme">🌓</button>
    </div>
  </header>

  <div class="layout">
    <nav id="sidebar" aria-label="Page navigation"></nav>
    <div class="overlay" id="overlay" hidden></div>
    <main id="content">
      <div id="docViewer"></div>
      <aside id="tocPanel" aria-label="On this page"></aside>
      <div class="footer-note">
        <span>Generated by <strong>MakeWiki.skills</strong></span>
        <span>Zero-Dependency Static Wiki</span>
      </div>
    </main>
  </div>

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

_SEARCH_BOX_HTML = """<div class="search-box">
      <span class="search-icon">🔍</span>
      <input type="text" id="searchInput" class="search-input" placeholder="Search docs..." aria-label="Search documentation" />
      <div id="searchPanel" class="search-panel" hidden></div>
    </div>"""

_SPA_CSS = """
    :root {
      --bg-primary: #ffffff;
      --bg-secondary: #f8fafc;
      --bg-sidebar: #f1f5f9;
      --border-color: #e2e8f0;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #94a3b8;
      --accent: #2563eb;
      --accent-hover: #1d4ed8;
      --code-bg: #1e293b;
      --code-text: #f8fafc;
      --alert-note-bg: #eff6ff;
      --alert-note-border: #3b82f6;
      --alert-warn-bg: #fffbeb;
      --alert-warn-border: #f59e0b;
      --sidebar-width: 280px;
      --toc-width: 240px;
      color-scheme: light;
    }
    [data-theme="dark"] {
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-sidebar: #131d31;
      --border-color: #334155;
      --text-primary: #f8fafc;
      --text-secondary: #cbd5e1;
      --text-muted: #64748b;
      --accent: #38bdf8;
      --accent-hover: #0ea5e9;
      --code-bg: #0b1120;
      --code-text: #e2e8f0;
      --alert-note-bg: #172554;
      --alert-note-border: #38bdf8;
      --alert-warn-bg: #451a03;
      --alert-warn-border: #f59e0b;
      color-scheme: dark;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }
    .skip-link {
      position: absolute;
      left: -9999px;
      top: 0;
      background: var(--accent);
      color: #fff;
      padding: 0.5rem 1rem;
      z-index: 200;
      border-radius: 0 0 6px 0;
    }
    .skip-link:focus { left: 0; }
    header {
      height: 60px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0 1.5rem;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .hamburger {
      display: none;
      background: transparent;
      border: none;
      color: var(--text-primary);
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      font-size: 1.15rem;
      color: var(--text-primary);
      text-decoration: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .badge {
      background: var(--accent);
      color: white;
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 9999px;
      font-weight: 600;
      flex-shrink: 0;
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 1rem;
      flex-shrink: 0;
    }
    .search-box { position: relative; }
    .search-input {
      padding: 0.4rem 0.8rem 0.4rem 2rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-primary);
      color: var(--text-primary);
      font-size: 0.875rem;
      width: 220px;
      transition: width 0.2s;
    }
    .search-input:focus { width: 300px; outline: 2px solid var(--accent); }
    .search-icon {
      position: absolute;
      left: 8px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 0.85rem;
      pointer-events: none;
    }
    .search-panel {
      position: absolute;
      top: calc(100% + 6px);
      right: 0;
      width: 400px;
      max-width: 90vw;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
      max-height: 70vh;
      overflow-y: auto;
      z-index: 100;
    }
    .search-result {
      display: block;
      padding: 0.7rem 1rem;
      cursor: pointer;
      border-bottom: 1px solid var(--border-color);
      text-decoration: none;
    }
    .search-result:last-child { border-bottom: none; }
    .search-result:hover, .search-result.active { background: var(--bg-secondary); }
    .search-result-title { font-weight: 600; color: var(--text-primary); }
    .search-result-title em { color: var(--accent); font-style: normal; }
    .search-result-snippet { font-size: 0.8rem; color: var(--text-secondary); }
    .search-empty { padding: 1rem; color: var(--text-muted); font-size: 0.9rem; }
    select, button.theme-btn {
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-primary);
      color: var(--text-primary);
      cursor: pointer;
      font-size: 0.875rem;
    }
    .layout { display: flex; flex: 1; min-height: 0; }
    #sidebar {
      width: var(--sidebar-width);
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      padding: 1.5rem 1rem;
      height: calc(100vh - 60px);
      position: sticky;
      top: 60px;
      overflow-y: auto;
      flex-shrink: 0;
    }
    .nav-group { margin-bottom: 1.5rem; }
    .nav-group-title {
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      padding-left: 0.5rem;
      letter-spacing: 0.05em;
    }
    .nav-item {
      display: block;
      padding: 0.4rem 0.75rem;
      color: var(--text-secondary);
      text-decoration: none;
      border-radius: 6px;
      font-size: 0.9rem;
      margin-bottom: 2px;
      transition: background 0.15s, color 0.15s;
      cursor: pointer;
    }
    .nav-item.child { padding-left: 1.5rem; font-size: 0.85rem; }
    .nav-item:hover { background: var(--border-color); color: var(--text-primary); }
    .nav-item.active { background: var(--accent); color: white; font-weight: 600; }
    main {
      flex: 1;
      padding: 2.5rem 3.5rem;
      max-width: 1200px;
      display: flex;
      gap: 2rem;
      min-width: 0;
    }
    #docViewer { flex: 1; min-width: 0; max-width: 820px; }
    #tocPanel {
      width: var(--toc-width);
      flex-shrink: 0;
      position: sticky;
      top: 80px;
      height: fit-content;
      align-self: flex-start;
      font-size: 0.85rem;
      border-left: 1px solid var(--border-color);
      padding-left: 1rem;
    }
    #tocPanel h4 { text-transform: uppercase; font-size: 0.7rem; color: var(--text-muted); letter-spacing: 0.05em; margin-bottom: 0.6rem; }
    #tocPanel a { display: block; color: var(--text-secondary); text-decoration: none; padding: 0.2rem 0; border-left: 2px solid transparent; padding-left: 0.6rem; }
    #tocPanel a:hover { color: var(--text-primary); }
    #tocPanel a.active { color: var(--accent); border-left-color: var(--accent); font-weight: 600; }
    #tocPanel a.lvl-3 { padding-left: 1.4rem; font-size: 0.8rem; }
    #docViewer h1 { font-size: 2.2rem; margin-bottom: 1rem; color: var(--text-primary); }
    #docViewer h2 { font-size: 1.5rem; margin-top: 2rem; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3rem; }
    #docViewer h3 { font-size: 1.2rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
    #docViewer h4 { font-size: 1.05rem; margin-top: 1.2rem; margin-bottom: 0.4rem; }
    #docViewer p { margin-bottom: 1rem; color: var(--text-secondary); font-size: 1.05rem; }
    #docViewer ul, #docViewer ol { margin-left: 1.5rem; margin-bottom: 1rem; color: var(--text-secondary); }
    #docViewer li { margin-bottom: 0.35rem; }
    #docViewer pre {
      background: var(--code-bg);
      color: var(--code-text);
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
      margin-bottom: 1.5rem;
      position: relative;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.9rem;
    }
    #docViewer code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.9em;
      background: var(--bg-secondary);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      color: var(--accent);
    }
    #docViewer pre code { background: transparent; padding: 0; color: inherit; }
    #docViewer a { color: var(--accent); text-decoration: none; }
    #docViewer a:hover { text-decoration: underline; color: var(--accent-hover); }
    .wiki-link { color: var(--accent); font-weight: 500; cursor: pointer; }
    .wiki-link:hover { text-decoration: underline; }
    .external-link { color: var(--accent); font-size: 0.95em; }
    .copy-btn {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      background: rgba(255,255,255,0.15);
      border: none;
      color: white;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      cursor: pointer;
    }
    .copy-btn:hover { background: rgba(255,255,255,0.3); }
    #docViewer table { width: 100%; border-collapse: collapse; margin: 1.5rem 0; display: block; overflow-x: auto; }
    #docViewer th, #docViewer td { border: 1px solid var(--border-color); padding: 0.6rem 0.9rem; text-align: left; font-size: 0.95rem; }
    #docViewer th { background: var(--bg-secondary); font-weight: 600; }
    #docViewer blockquote {
      border-left: 4px solid var(--alert-note-border);
      background: var(--alert-note-bg);
      padding: 0.8rem 1rem;
      border-radius: 0 6px 6px 0;
      margin: 1.2rem 0;
    }
    .alert-warn { border-left-color: var(--alert-warn-border); background: var(--alert-warn-bg); }
    #docViewer hr { border: 0; border-top: 1px solid var(--border-color); margin: 2rem 0; }
    .fallback-banner {
      background: var(--alert-warn-bg);
      border: 1px solid var(--alert-warn-border);
      color: var(--text-secondary);
      padding: 0.6rem 1rem;
      border-radius: 6px;
      font-size: 0.9rem;
      margin-bottom: 1.5rem;
    }
    .footer-note {
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border-color);
      color: var(--text-muted);
      font-size: 0.85rem;
      display: flex;
      justify-content: space-between;
    }
    .overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
      z-index: 40;
    }
    :focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    @media (max-width: 1100px) { #tocPanel { display: none; } }
    @media (max-width: 768px) {
      header { padding: 0 0.75rem; height: 56px; }
      .hamburger { display: block; }
      .brand .badge { display: none; }
      .search-input, .search-input:focus { width: 120px; }
      .layout { flex-direction: column; }
      #sidebar {
        position: fixed;
        top: 56px;
        left: 0;
        bottom: 0;
        width: var(--sidebar-width);
        height: auto;
        transform: translateX(-100%);
        transition: transform 0.25s ease;
        z-index: 45;
        box-shadow: 2px 0 8px rgba(0,0,0,0.1);
      }
      #sidebar.open { transform: translateX(0); }
      .overlay.open { display: block; }
      main { padding: 1.5rem 1rem; flex-direction: column; }
      #docViewer { overflow-x: auto; }
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
            groupIndex[ni.group] = groups.length;
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
          a.onclick = (e) => { e.preventDefault(); navigateTo(currentLang, ni.route, true); };
          grp.appendChild(a);
        });
        sidebar.appendChild(grp);
      });
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
    }

    function initTheme() {
      const stored = (() => { try { return localStorage.getItem('site-theme'); } catch (e) { return null; } })();
      const pref = stored || siteConfig.visual.theme || 'auto';
      const resolved = pref === 'auto' ? (prefersDark() ? 'dark' : 'light') : pref;
      applyTheme(resolved);
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

    // --- mobile drawer ---

    function openDrawer() {
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('overlay');
      const burger = document.getElementById('hamburger');
      sidebar.classList.add('open');
      overlay.hidden = false;
      overlay.classList.add('open');
      burger.setAttribute('aria-expanded', 'true');
    }

    function closeDrawer() {
      const sidebar = document.getElementById('sidebar');
      const overlay = document.getElementById('overlay');
      const burger = document.getElementById('hamburger');
      sidebar.classList.remove('open');
      if (overlay) { overlay.hidden = true; overlay.classList.remove('open'); }
      burger.setAttribute('aria-expanded', 'false');
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

    // --- code copy (event-delegated) ---

    function attachCopyButtons() {
      const viewer = document.getElementById('docViewer');
      viewer.querySelectorAll('pre').forEach(pre => {
        if (pre.querySelector('.copy-btn')) return;
        const btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.textContent = 'Copy';
        btn.setAttribute('aria-label', 'Copy code block');
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const code = pre.querySelector('code');
          const text = code ? code.innerText : pre.innerText;
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
        pre.appendChild(btn);
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
      if (!results.length) {
        const empty = document.createElement('div');
        empty.className = 'search-empty';
        empty.textContent = 'No results for "' + query + '"';
        panel.appendChild(empty);
        panel.hidden = false;
        return;
      }
      results.forEach(r => {
        const a = document.createElement('a');
        a.className = 'search-result';
        a.href = '#' + r.route;
        a.setAttribute('data-route', r.route);
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
          closeSearch();
          navigateTo(currentLang, r.route, true);
        });
        panel.appendChild(a);
      });
      panel.hidden = false;
    }

    function handleSearch(e) {
      const query = e.target.value.toLowerCase().trim();
      const panel = document.getElementById('searchPanel');
      if (!panel) return;
      if (!query) { panel.hidden = true; return; }
      if (!searchIndex) searchIndex = buildSearchIndex();
      const results = searchIndex.filter(r =>
        r.titleLower.indexOf(query) !== -1 || r.text.indexOf(query) !== -1
      ).slice(0, 12);
      renderSearchResults(query, results);
    }

    function closeSearch() {
      const panel = document.getElementById('searchPanel');
      const input = document.getElementById('searchInput');
      if (panel) panel.hidden = true;
      if (input) input.value = '';
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
      if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
        searchInput.addEventListener('focus', () => {
          if (searchInput.value && searchInput.value.trim()) handleSearch({ target: searchInput });
        });
        searchInput.addEventListener('keydown', (e) => {
          if (e.key === 'Escape') closeSearch();
        });
        document.addEventListener('click', (e) => {
          const panel = document.getElementById('searchPanel');
          if (panel && !panel.contains(e.target) && e.target.id !== 'searchInput') panel.hidden = true;
        });
        document.addEventListener('keydown', (e) => {
          if ((e.key === '/' && document.activeElement !== searchInput) ||
              ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k')) {
            e.preventDefault();
            searchInput.focus();
          }
        });
      }

      const burger = document.getElementById('hamburger');
      if (burger) burger.addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        if (sidebar.classList.contains('open')) closeDrawer();
        else openDrawer();
      });
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
