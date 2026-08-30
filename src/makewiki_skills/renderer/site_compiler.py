"""Static Wiki Website Compiler (plan-driven, mechanical renderer).

Compiles generated Markdown wiki documentation into an offline, zero-dependency,
responsive static website with multilingual switcher, dark/light theme, and
search.

The compiler is a PURE MECHANICAL renderer. It consumes an LLM-authored
:class:`~makewiki_skills.model.site_presentation.SitePresentationPlan` that
declares the site's Information Architecture (navigation groups, page order,
routes, hierarchy, localized titles) and visual direction, and renders exactly
that plan. It performs NO semantic page classification:

* It never infers a page role (Overview / Getting Started / FAQ / Deployment /
  etc.), navigation group, ordering, or hierarchy from a filename or keyword.
* It locates each document purely by the plan's stable ``document_id`` and
  resolves the localized Markdown content mechanically.
* Without a plan it refuses to compile — it does NOT fabricate an IA — so a
  missing plan leaves site build in an ``unavailable``/``pending`` state that
  never blocks the Main Agent's cognitive work.

This is the Cognitive Authority Boundary for the site: the Main Agent / Site
Designer LLM authorises the plan; Python only packages it.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from makewiki_skills.model.site_presentation import (
    SiteNavItem,
    SitePresentationPlan,
)


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
        match = re.search(r"^#\s+(.+)$", content_md, re.MULTILINE)
        return match.group(1).strip() if match else None

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
    ) -> dict[str, dict[str, dict[str, str]]]:
        """Mechanically resolve each plan-referenced document's Markdown.

        Returns ``{ lang: { document_id: {"markdown": ..., "title": ...} } }``.
        The document set is EXACTLY the plan's navigation — Python never adds
        documents, groups, or ordering of its own. A document missing for a
        given language is omitted from that language (mechanical absence); a
        plan reference with no file at all is a plan error the renderer surfaces.
        """
        content_by_lang: dict[str, dict[str, dict[str, str]]] = {
            lang: {} for lang in plan.languages
        }
        missing: list[str] = []

        # Resolve root + child nav items; ordering/grouping come from the plan.
        nav_items = self._flatten_nav_items(plan.navigation)

        for lang in plan.languages:
            for item in nav_items:
                path = self._lang_document_path(makewiki_dir, item.document_id, lang)
                if not path.is_file():
                    # Recorded so effective languages can be computed; not an
                    # error the renderer should fail on (a doc may be absent for
                    # one language while present for another).
                    missing.append(f"{item.document_id}.{lang}")
                    continue
                content_md = path.read_text(encoding="utf-8", errors="replace")
                content_by_lang[lang][item.document_id] = {
                    "markdown": content_md,
                    "title": self._extract_h1(content_md) or item.title,
                }

        return content_by_lang

    def _render_spa_html(
        self,
        content_by_lang: dict[str, dict[str, dict[str, str]]],
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
        languages = [
            lang for lang in plan.languages if content_by_lang.get(lang)
        ] or [plan.default_language]

        site_config: dict[str, Any] = {
            "projectTitle": plan.project_title,
            "projectDescription": plan.project_description,
            "defaultLang": plan.default_language if plan.default_language in languages else languages[0],
            "languages": languages,
            "visual": {
                "theme": plan.visual.theme,
                "include_search": plan.visual.include_search,
                "accentColor": plan.visual.accent_color,
                "brandLabel": plan.visual.brand_label,
            },
        }
        site_nav: list[dict[str, Any]] = [_nav_item_dict(item) for item in plan.navigation]

        # Content keyed by lang -> document_id -> markdown, for the JS viewer.
        docs_json_obj: dict[str, dict[str, str]] = {}
        for lang, docs in content_by_lang.items():
            docs_json_obj[lang] = {
                doc_id: entry["markdown"] for doc_id, entry in docs.items()
            }

        config_json = json.dumps(site_config, ensure_ascii=False)
        nav_json = json.dumps(site_nav, ensure_ascii=False)
        docs_json = json.dumps(docs_json_obj, ensure_ascii=False)

        search_box_html = (
            """<div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" class="search-input" placeholder="Search docs..." />
      </div>"""
            if plan.visual.include_search
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(plan.project_title)} - MakeWiki</title>
  <style>
    :root {{
      --bg-primary: #ffffff;
      --bg-secondary: #f8fafc;
      --bg-sidebar: #f1f5f9;
      --border-color: #e2e8f0;
      --text-primary: #0f172a;
      --text-secondary: #475569;
      --text-muted: #94a3b8;
      --accent: {plan.visual.accent_color or '#2563eb'};
      --accent-hover: #1d4ed8;
      --code-bg: #1e293b;
      --code-text: #f8fafc;
      --alert-note-bg: #eff6ff;
      --alert-note-border: #3b82f6;
      --alert-warn-bg: #fffbeb;
      --alert-warn-border: #f59e0b;
      --sidebar-width: 280px;
    }}
    [data-theme="dark"] {{
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-sidebar: #131d31;
      --border-color: #334155;
      --text-primary: #f8fafc;
      --text-secondary: #cbd5e1;
      --text-muted: #64748b;
      --accent: {plan.visual.accent_color or '#38bdf8'};
      --accent-hover: #0ea5e9;
      --code-bg: #0b1120;
      --code-text: #e2e8f0;
      --alert-note-bg: #172554;
      --alert-note-border: #38bdf8;
      --alert-warn-bg: #451a03;
      --alert-warn-border: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }}
    header {{
      height: 60px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1.5rem;
      position: sticky;
      top: 0;
      z-index: 50;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-weight: 700;
      font-size: 1.15rem;
      color: var(--text-primary);
      text-decoration: none;
    }}
    .badge {{
      background: var(--accent);
      color: white;
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 9999px;
      font-weight: 600;
    }}
    .nav-actions {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .search-box {{
      position: relative;
    }}
    .search-input {{
      padding: 0.4rem 0.8rem 0.4rem 2rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-primary);
      color: var(--text-primary);
      font-size: 0.875rem;
      width: 220px;
      transition: width 0.2s;
    }}
    .search-input:focus {{
      width: 300px;
      outline: 2px solid var(--accent);
    }}
    .search-icon {{
      position: absolute;
      left: 8px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      font-size: 0.85rem;
    }}
    select, button.theme-btn {{
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: var(--bg-primary);
      color: var(--text-primary);
      cursor: pointer;
      font-size: 0.875rem;
    }}
    .layout {{
      display: flex;
      flex: 1;
    }}
    aside {{
      width: var(--sidebar-width);
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      padding: 1.5rem 1rem;
      height: calc(100vh - 60px);
      position: sticky;
      top: 60px;
      overflow-y: auto;
    }}
    .nav-group {{
      margin-bottom: 1.5rem;
    }}
    .nav-group-title {{
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 0.5rem;
      padding-left: 0.5rem;
      letter-spacing: 0.05em;
    }}
    .nav-item {{
      display: block;
      padding: 0.4rem 0.75rem;
      color: var(--text-secondary);
      text-decoration: none;
      border-radius: 6px;
      font-size: 0.9rem;
      margin-bottom: 2px;
      transition: background 0.15s, color 0.15s;
      cursor: pointer;
    }}
    .nav-item.child {{
      padding-left: 1.5rem;
      font-size: 0.85rem;
    }}
    .nav-item:hover {{
      background: var(--border-color);
      color: var(--text-primary);
    }}
    .nav-item.active {{
      background: var(--accent);
      color: white;
      font-weight: 600;
    }}
    main {{
      flex: 1;
      padding: 2.5rem 3.5rem;
      max-width: 960px;
      overflow-y: auto;
    }}
    .content-card {{
      background: var(--bg-primary);
    }}
    h1 {{ font-size: 2.2rem; margin-bottom: 1rem; color: var(--text-primary); }}
    h2 {{ font-size: 1.5rem; margin-top: 2rem; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3rem; }}
    h3 {{ font-size: 1.2rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }}
    p {{ margin-bottom: 1rem; color: var(--text-secondary); font-size: 1.05rem; }}
    ul, ol {{ margin-left: 1.5rem; margin-bottom: 1rem; color: var(--text-secondary); }}
    li {{ margin-bottom: 0.35rem; }}
    pre {{
      background: var(--code-bg);
      color: var(--code-text);
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
      margin-bottom: 1.5rem;
      position: relative;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.9rem;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.9em;
      background: var(--bg-secondary);
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      color: var(--accent);
    }}
    pre code {{
      background: transparent;
      padding: 0;
      color: inherit;
    }}
    a {{
      color: var(--accent);
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
      color: var(--accent-hover);
    }}
    .wiki-link {{
      color: var(--accent);
      font-weight: 500;
      cursor: pointer;
    }}
    .wiki-link:hover {{
      text-decoration: underline;
    }}
    .external-link {{
      color: var(--accent);
      font-size: 0.95em;
    }}
    .copy-btn {{
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
    }}
    .copy-btn:hover {{
      background: rgba(255,255,255,0.3);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1.5rem 0;
    }}
    th, td {{
      border: 1px solid var(--border-color);
      padding: 0.6rem 0.9rem;
      text-align: left;
      font-size: 0.95rem;
    }}
    th {{
      background: var(--bg-secondary);
      font-weight: 600;
    }}
    blockquote {{
      border-left: 4px solid var(--alert-note-border);
      background: var(--alert-note-bg);
      padding: 0.8rem 1rem;
      border-radius: 0 6px 6px 0;
      margin: 1.2rem 0;
    }}
    .alert-warn {{
      border-left-color: var(--alert-warn-border);
      background: var(--alert-warn-bg);
    }}
    hr {{
      border: 0;
      border-top: 1px solid var(--border-color);
      margin: 2rem 0;
    }}
    .footer-note {{
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border-color);
      color: var(--text-muted);
      font-size: 0.85rem;
      display: flex;
      justify-content: space-between;
    }}
    @media (max-width: 768px) {{
      .layout {{ flex-direction: column; }}
      aside {{ width: 100%; height: auto; position: static; }}
      main {{ padding: 1.5rem 1rem; }}
    }}
  </style>
</head>
<body>
  <header>
    <a href="#" onclick="navigateTo(siteConfig.defaultLang, null, true); return false;" class="brand">
      <span>📚 {html.escape(plan.visual.brand_label)}</span>
      <span class="badge">Offline Docs</span>
    </a>
    <div class="nav-actions">
      {search_box_html}
      <select id="langSelect"></select>
      <button class="theme-btn" id="themeToggle">🌓</button>
    </div>
  </header>

  <div class="layout">
    <aside id="sidebar"></aside>
    <main>
      <div class="content-card" id="docViewer"></div>
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

    let currentLang = siteConfig.defaultLang;
    let currentRoute = null;

    // --- navigation helpers (nav structure comes ONLY from the plan) ---

    function allNavItems() {{
      const out = [];
      siteNav.forEach(group => {{
        out.push(group);
        (group.children || []).forEach(c => out.push(c));
      }});
      return out;
    }}

    function navItemByRoute(route) {{
      return allNavItems().find(i => i.route === route) || null;
    }}

    function navItemByHome() {{ return siteNav.length ? siteNav[0] : null; }}

    function activeNavItem() {{
      if (currentRoute) {{
        const byRoute = navItemByRoute(currentRoute);
        if (byRoute) return byRoute;
      }}
      return navItemByHome();
    }}

    function itemTitle(item, lang) {{
      return (item.titles && item.titles[lang]) || item.title;
    }}

    function hasContent(item, lang) {{
      return !!(docsContent[lang] && docsContent[lang][item.id]);
    }}

    function firstRoutableItem(lang) {{
      return allNavItems().find(i => hasContent(i, lang)) || null;
    }}

    // --- language + theme ---

    function getLangLabel(code) {{
      const map = {{ 'en': 'English', 'zh-CN': '简体中文', 'ja': '日本語', 'de': 'Deutsch', 'fr': 'Français' }};
      return map[code] || code;
    }}

    function toggleTheme() {{
      const root = document.documentElement;
      const cur = root.getAttribute('data-theme');
      const next = cur === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
    }}

    // --- navigation ---

    function navigateTo(lang, route, updateHash) {{
      if (lang) currentLang = lang;
      if (route !== undefined && route !== null) currentRoute = route;
      else {{
        const item = activeNavItem();
        currentRoute = item ? item.route : (firstRoutableItem(currentLang) || {{route: '#'}}).route;
      }}
      if (siteConfig.languages.indexOf(currentLang) === -1) {{
        currentLang = siteConfig.defaultLang;
      }}
      if (updateHash && window.location.hash !== ('#' + currentRoute)) {{
        window.location.hash = '#' + currentRoute;
      }}
      renderSidebar();
      renderDoc();
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    // --- sidebar rendering (painting the plan's IA, verbatim) ---

    function renderSidebar(filteredIds = null) {{
      const sidebar = document.getElementById('sidebar');
      sidebar.innerHTML = '';
      const active = activeNavItem();

      // Group plan items by nav_group, preserving plan order.
      const groups = [];
      const groupIndex = {{}};
      siteNav.forEach(item => {{
        const items = [item].concat(item.children || []);
        items.forEach(ni => {{
          if (filteredIds && filteredIds.indexOf(ni.id) === -1) return;
          let g = groupIndex[ni.group];
          if (g === undefined) {{
            g = {{ name: ni.group, items: [] }};
            groupIndex[ni.group] = groups.length;
            groups.push(g);
          }}
          g.items.push(ni);
        }});
      }});

      groups.forEach(g => {{
        g.items.sort((a, b) => a.order - b.order);
        const grp = document.createElement('div');
        grp.className = 'nav-group';
        const title = document.createElement('div');
        title.className = 'nav-group-title';
        title.textContent = g.name;
        grp.appendChild(title);
        g.items.forEach(ni => {{
          const a = document.createElement('a');
          const isActive = active && ni.route === active.route;
          a.className = 'nav-item' + (ni.parent ? ' child' : '') + (isActive ? ' active' : '');
          a.textContent = itemTitle(ni, currentLang);
          a.href = '#' + ni.route;
          a.setAttribute('data-route', ni.route);
          a.onclick = (e) => {{ e.preventDefault(); navigateTo(currentLang, ni.route, true); }};
          grp.appendChild(a);
        }});
        sidebar.appendChild(grp);
      }});
    }}

    // --- search ---

    function handleSearch(e) {{
      const query = e.target.value.toLowerCase().trim();
      if (!query) {{ renderSidebar(); return; }}
      const items = allNavItems();
      const matched = items.filter(ni => {{
        const md = docsContent[currentLang] && docsContent[currentLang][ni.id];
        const hay = itemTitle(ni, currentLang).toLowerCase() + '\\n' + (md ? md.toLowerCase() : '');
        return hay.includes(query);
      }}).map(ni => ni.id);
      renderSidebar(matched);
    }}

    // --- document rendering ---

    function currentDocMarkdown() {{
      const item = activeNavItem();
      if (!item) return null;
      const md = docsContent[currentLang] && docsContent[currentLang][item.id];
      if (md) return md;
      // Cross-language fallback: render the default-language content if this
      // language has no file, so a partially-localized site still reads.
      if (currentLang !== siteConfig.defaultLang && docsContent[siteConfig.defaultLang]) {{
        const fallback = docsContent[siteConfig.defaultLang][item.id];
        if (fallback) return fallback;
      }}
      return null;
    }}

    function renderDoc() {{
      const viewer = document.getElementById('docViewer');
      const item = activeNavItem();
      const md = currentDocMarkdown();
      if (!item || md === null) {{
        const home = navItemByHome();
        const homeRoute = home ? home.route : '#';
        viewer.innerHTML = `<h1>Document Not Found</h1><p>The requested page could not be found.</p><p><a href="#${{homeRoute}}" onclick="navigateTo(null, '${{homeRoute}}', true); return false;" class="wiki-link">← Return to Overview</a></p>`;
        return;
      }}
      viewer.innerHTML = parseMarkdownToHtml(md);
    }}

    // --- init ---

    function init() {{
      const theme = siteConfig.visual.theme;
      if (theme === 'dark' || theme === 'light') {{
        document.documentElement.setAttribute('data-theme', theme);
      }}
      const langSelect = document.getElementById('langSelect');
      langSelect.innerHTML = '';
      siteConfig.languages.forEach(lang => {{
        const opt = document.createElement('option');
        opt.value = lang;
        opt.textContent = getLangLabel(lang);
        langSelect.appendChild(opt);
      }});
      langSelect.value = currentLang;
      langSelect.addEventListener('change', (e) => {{ navigateTo(e.target.value, null, true); }});

      window.addEventListener('hashchange', () => {{
        if (window.location.hash && window.location.hash.length > 1) {{
          const route = decodeURIComponent(window.location.hash.slice(1));
          if (route !== currentRoute) navigateTo(currentLang, route, false);
        }}
      }});

      document.getElementById('themeToggle').addEventListener('click', toggleTheme);
      const searchInput = document.getElementById('searchInput');
      if (searchInput) searchInput.addEventListener('input', handleSearch);

      // Start at the URL hash route, else the first routable item.
      if (window.location.hash && window.location.hash.length > 1) {{
        currentRoute = decodeURIComponent(window.location.hash.slice(1));
      }} else {{
        const first = firstRoutableItem(currentLang);
        currentRoute = first ? first.route : (navItemByHome() || {{route: '#'}}).route;
      }}
      renderSidebar();
      renderDoc();
    }}

    function resolveInternalSlug(target) {{
      let clean = target.trim();
      if (clean.startsWith('./')) clean = clean.slice(2);
      const hashIdx = clean.indexOf('#');
      if (hashIdx !== -1) clean = clean.slice(0, hashIdx);
      clean = clean.replace(/\\.([a-z]{{2}}(?:-[A-Z]{{2,4}})?)?\\.md$/i, '').replace(/\\.md$/i, '');
      return clean;
    }}

    function parseMarkdownToHtml(md) {{
      let html = md;

      // 1. Protect Code blocks
      const codeBlocks = [];
      html = html.replace(/```(\\w*)\\n([\\s\\S]*?)```/g, (match, lang, code) => {{
        const placeholder = `__CODE_BLOCK_${{codeBlocks.length}}__`;
        codeBlocks.push(`<pre><button class="copy-btn" onclick="copyCode(this)">Copy</button><code class="language-${{lang}}">${{escapeHtml(code.trim())}}</code></pre>`);
        return placeholder;
      }});

      // 2. Protect Inline code
      const inlineCodes = [];
      html = html.replace(/`([^`]+)`/g, (match, code) => {{
        const placeholder = `__INLINE_CODE_${{inlineCodes.length}}__`;
        inlineCodes.push(`<code>${{escapeHtml(code)}}</code>`);
        return placeholder;
      }});

      // 3. Headers
      html = html.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
      html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
      html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
      html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

      // 4. Alerts / Blockquotes
      html = html.replace(/^> \\[!(NOTE|TIP|IMPORTANT)\\]\\s*\\n> (.*$)/gim, '<blockquote><strong>$1:</strong> $2</blockquote>');
      html = html.replace(/^> \\[!(WARNING|CAUTION)\\]\\s*\\n> (.*$)/gim, '<blockquote class="alert-warn"><strong>$1:</strong> $2</blockquote>');
      html = html.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

      // 5. Horizontal rules
      html = html.replace(/^---+$/gim, '<hr>');

      // 6. Tables
      html = html.replace(/\\|(.+)\\|\\n\\|[-:\\| ]+\\|\\n((?:\\|.+\\|\\n?)+)/g, (match, header, rows) => {{
        const ths = header.split('|').map(s => s.trim()).filter(Boolean).map(h => `<th>${{h}}</th>`).join('');
        const trs = rows.trim().split('\\n').map(r => {{
          const tds = r.split('|').map(s => s.trim()).filter(Boolean).map(d => `<td>${{d}}</td>`).join('');
          return `<tr>${{tds}}</tr>`;
        }}).join('');
        return `<table><thead><tr>${{ths}}</tr></thead><tbody>${{trs}}</tbody></table>`;
      }});

      // 7. Markdown Links: [Text](URL)
      html = html.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, (match, text, url) => {{
        const cleanUrl = url.trim();
        if (cleanUrl.startsWith('http://') || cleanUrl.startsWith('https://') || cleanUrl.startsWith('mailto:')) {{
          return `<a href="${{cleanUrl}}" target="_blank" rel="noopener" class="external-link">${{text}} ↗</a>`;
        }}
        if (cleanUrl.startsWith('#')) {{
          return `<a href="${{cleanUrl}}" class="anchor-link">${{text}}</a>`;
        }}
        const targetSlug = resolveInternalSlug(cleanUrl);
        const target = allNavItems().find(ni => ni.id === targetSlug || ni.id.toLowerCase() === targetSlug.toLowerCase());
        const route = target ? target.route : targetSlug;
        return `<a href="#${{route}}" class="wiki-link" onclick="navigateTo(null, '${{route}}', true); return false;">${{text}}</a>`;
      }});

      // 8. Bold, italic
      html = html.replace(/\\*\\*([^\\*]+)\\*\\*/g, '<strong>$1</strong>');
      html = html.replace(/\\*([^\\*]+)\\*/g, '<em>$1</em>');

      // 9. Lists
      html = html.replace(/^\\s*[-*]\\s+(.*$)/gim, '<li>$1</li>');
      html = html.replace(/^\\s*\\d+\\.\\s+(.*$)/gim, '<li>$1</li>');
      html = html.replace(/((?:<li>.*<\\/li>\\s*)+)/g, '<ul>$1</ul>');

      // 10. Paragraphs
      html = html.split('\\n\\n').map(p => {{
        const trimmed = p.trim();
        if (!trimmed) return '';
        if (trimmed.startsWith('<h') || trimmed.startsWith('__CODE_BLOCK_') || trimmed.startsWith('<table') ||
            trimmed.startsWith('<blockquote') || trimmed.startsWith('<ul') || trimmed.startsWith('<ol') || trimmed.startsWith('<hr')) {{
          return trimmed;
        }}
        return `<p>${{trimmed}}</p>`;
      }}).join('\\n');

      // 11. Restore Inline code
      inlineCodes.forEach((code, idx) => {{
        html = html.replace(`__INLINE_CODE_${{idx}}__`, code);
      }});

      // 12. Restore Code blocks
      codeBlocks.forEach((code, idx) => {{
        html = html.replace(`__CODE_BLOCK_${{idx}}__`, code);
      }});

      return html;
    }}

    function escapeHtml(str) {{
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }}

    function copyCode(btn) {{
      const code = btn.nextElementSibling.innerText;
      navigator.clipboard.writeText(code).then(() => {{
        const orig = btn.innerText;
        btn.innerText = 'Copied!';
        setTimeout(() => btn.innerText = orig, 1500);
      }});
    }}

    window.addEventListener('DOMContentLoaded', init);
  </script>
</body>
</html>"""
