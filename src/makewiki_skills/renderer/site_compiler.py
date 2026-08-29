"""Static Wiki Website Compiler.

Compiles generated Markdown wiki documentation into an offline, zero-dependency,
responsive static website with multilingual switcher, dark/light theme, and search.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any


class SiteCompiler:
    """Compiles a directory of makewiki Markdown files into a standalone static site."""

    def __init__(self, theme: str = "auto", title: str = "Project Documentation") -> None:
        self.theme = theme
        self.title = title

    def compile(self, makewiki_dir: Path, output_dir: Path | None = None) -> list[str]:
        """Compile Markdown files in makewiki_dir into output_dir/site."""
        makewiki_dir = Path(makewiki_dir).resolve()
        if not makewiki_dir.is_dir():
            raise ValueError(f"MakeWiki directory does not exist: {makewiki_dir}")

        if output_dir is None:
            site_dir = makewiki_dir / "site"
        else:
            site_dir = Path(output_dir).resolve()

        site_dir.mkdir(parents=True, exist_ok=True)

        docs = self._collect_documents(makewiki_dir)
        html_content = self._render_spa_html(docs, self.title, self.theme)

        index_file = site_dir / "index.html"
        index_file.write_text(html_content, encoding="utf-8")

        return [str(index_file)]

    def _collect_documents(self, root_dir: Path) -> dict[str, dict[str, dict[str, Any]]]:
        """Group documents by language and doc slug."""
        # result: { "en": { "readme": { "title": "...", "content": "...", "category": "..." } } }
        docs_by_lang: dict[str, dict[str, dict[str, Any]]] = {}

        # Look for all .md files in root_dir and subdirs (like usage/)
        for md_file in sorted(root_dir.rglob("*.md")):
            # Skip site/ directory if inside makewiki_dir
            if "site" in md_file.parts:
                continue

            rel_path = md_file.relative_to(root_dir)
            rel_str = str(rel_path).replace("\\", "/")

            lang = "en"
            base_slug = rel_str[:-3]  # strip .md

            # Check language suffix e.g. README.zh-CN.md, usage/overview.ja.md
            match = re.search(r"\.([a-z]{2}(?:-[A-Z]{2,4})?)$", base_slug, re.IGNORECASE)
            if match:
                lang = match.group(1)
                base_slug = base_slug[: match.start()]

            # Determine category and sort priority
            category, title, priority = self._categorize_doc(base_slug, md_file)
            content_md = md_file.read_text(encoding="utf-8")

            # Extract H1 title if available
            h1_match = re.search(r"^#\s+(.+)$", content_md, re.MULTILINE)
            if h1_match:
                title = h1_match.group(1).strip()

            docs_by_lang.setdefault(lang, {})[base_slug] = {
                "slug": base_slug,
                "title": title,
                "category": category,
                "priority": priority,
                "markdown": content_md,
                "rel_path": rel_str,
            }

        return docs_by_lang

    @staticmethod
    def _categorize_doc(slug: str, file_path: Path) -> tuple[str, str, int]:
        slug_lower = slug.lower()
        if slug_lower in ("readme", "index"):
            return "Overview", "Project Overview", 10
        elif slug_lower.startswith("getting-started"):
            return "Getting Started", "Quick Start", 20
        elif slug_lower.startswith("installation") or slug_lower.startswith("deployment"):
            return "Installation & Deployment", "Installation & Runbook", 30
        elif slug_lower.startswith("configuration") or slug_lower.startswith(
            "environment-variables"
        ):
            return "Configuration", "Configuration Reference", 40
        elif slug_lower.startswith("usage"):
            subname = slug_lower.replace("usage/", "").replace("usage\\", "").capitalize()
            return "Usage & Workflows", f"Usage - {subname}", 50
        elif slug_lower.startswith("troubleshooting"):
            return "Operations & Support", "Troubleshooting & Incident Runbook", 60
        elif slug_lower.startswith("faq"):
            return "FAQ", "Frequently Asked Questions", 70
        else:
            return "Reference", slug.replace("-", " ").title(), 80

    def _render_spa_html(
        self, docs_by_lang: dict[str, dict[str, dict[str, Any]]], title: str, theme: str
    ) -> str:
        docs_json = json.dumps(docs_by_lang, ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html lang="en" data-theme="{theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} - MakeWiki</title>
  <style>
    :root {{
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
    }}
    [data-theme="dark"] {{
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
    <a href="#" onclick="navigateTo('README'); return false;" class="brand">
      <span>📚 MakeWiki</span>
      <span class="badge">Offline Docs</span>
    </a>
    <div class="nav-actions">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" id="searchInput" class="search-input" placeholder="Search docs..." />
      </div>
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
    const docsData = {docs_json};
    let currentLang = Object.keys(docsData)[0] || 'en';
    let currentSlug = 'README';

    function init() {{
      const langSelect = document.getElementById('langSelect');
      langSelect.innerHTML = '';
      Object.keys(docsData).forEach(lang => {{
        const opt = document.createElement('option');
        opt.value = lang;
        opt.textContent = getLangLabel(lang);
        langSelect.appendChild(opt);
      }});

      // Pick starting slug from URL hash if given
      if (window.location.hash && window.location.hash.length > 1) {{
        currentSlug = decodeURIComponent(window.location.hash.slice(1));
      }} else if (docsData[currentLang] && !findDoc(currentSlug)) {{
        currentSlug = Object.keys(docsData[currentLang])[0] || 'README';
      }}

      langSelect.value = currentLang;
      langSelect.addEventListener('change', (e) => {{
        currentLang = e.target.value;
        renderSidebar();
        renderDoc(currentSlug);
      }});

      window.addEventListener('hashchange', () => {{
        if (window.location.hash && window.location.hash.length > 1) {{
          const targetSlug = decodeURIComponent(window.location.hash.slice(1));
          if (targetSlug !== currentSlug) {{
            navigateTo(targetSlug, false);
          }}
        }}
      }});

      document.getElementById('themeToggle').addEventListener('click', toggleTheme);
      document.getElementById('searchInput').addEventListener('input', handleSearch);

      renderSidebar();
      renderDoc(currentSlug);
    }}

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

    function navigateTo(slug, updateHash = true) {{
      if (!slug) return;
      currentSlug = slug;
      if (updateHash) {{
        window.location.hash = '#' + slug;
      }}
      document.querySelectorAll('.nav-item').forEach(el => {{
        const itemSlug = el.getAttribute('data-slug');
        const isActive = itemSlug === slug || (itemSlug && itemSlug.toLowerCase() === slug.toLowerCase());
        el.classList.toggle('active', !!isActive);
      }});
      renderDoc(slug);
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
    }}

    function renderSidebar(filteredSlugs = null) {{
      const sidebar = document.getElementById('sidebar');
      sidebar.innerHTML = '';

      const langDocs = docsData[currentLang] || {{}};
      const categories = {{}};

      Object.values(langDocs).forEach(doc => {{
        if (filteredSlugs && !filteredSlugs.includes(doc.slug)) return;
        if (!categories[doc.category]) categories[doc.category] = [];
        categories[doc.category].push(doc);
      }});

      Object.entries(categories).forEach(([catName, docs]) => {{
        docs.sort((a, b) => a.priority - b.priority);
        const grp = document.createElement('div');
        grp.className = 'nav-group';

        const title = document.createElement('div');
        title.className = 'nav-group-title';
        title.textContent = catName;
        grp.appendChild(title);

        docs.forEach(doc => {{
          const item = document.createElement('a');
          const isActive = doc.slug === currentSlug || doc.slug.toLowerCase() === currentSlug.toLowerCase();
          item.className = 'nav-item' + (isActive ? ' active' : '');
          item.textContent = doc.title;
          item.href = '#' + doc.slug;
          item.setAttribute('data-slug', doc.slug);
          item.onclick = (e) => {{
            e.preventDefault();
            navigateTo(doc.slug);
          }};
          grp.appendChild(item);
        }});

        sidebar.appendChild(grp);
      }});
    }}

    function handleSearch(e) {{
      const query = e.target.value.toLowerCase().trim();
      if (!query) {{
        renderSidebar();
        return;
      }}

      const langDocs = docsData[currentLang] || {{}};
      const matched = Object.values(langDocs).filter(d =>
        d.title.toLowerCase().includes(query) || d.markdown.toLowerCase().includes(query)
      ).map(d => d.slug);

      renderSidebar(matched);
    }}

    function findDoc(slug) {{
      if (!slug) return null;
      const langDocs = docsData[currentLang] || {{}};
      if (langDocs[slug]) return langDocs[slug];
      const lower = slug.toLowerCase();
      for (const k in langDocs) {{
        if (k.toLowerCase() === lower) return langDocs[k];
      }}
      if (docsData['en']) {{
        if (docsData['en'][slug]) return docsData['en'][slug];
        for (const k in docsData['en']) {{
          if (k.toLowerCase() === lower) return docsData['en'][k];
        }}
      }}
      return null;
    }}

    function renderDoc(slug) {{
      const doc = findDoc(slug);
      const viewer = document.getElementById('docViewer');
      if (!doc) {{
        viewer.innerHTML = `<h1>Document Not Found</h1><p>The requested page <code>${{escapeHtml(slug)}}</code> does not exist in this language.</p><p><a href="#README" onclick="navigateTo('README'); return false;" class="wiki-link">← Return to Overview</a></p>`;
        return;
      }}

      viewer.innerHTML = parseMarkdownToHtml(doc.markdown);
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
        return `<a href="#${{targetSlug}}" class="wiki-link" onclick="navigateTo('${{targetSlug}}'); return false;">${{text}}</a>`;
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
