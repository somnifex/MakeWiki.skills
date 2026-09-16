"""Single-file documentation exporters for PDF-ready HTML, EPUB, and offline printable bundles.

Markdown conversion goes through the SAME mechanical pipeline as the static
site (:func:`makewiki_skills.renderer.markdown_render.render_markdown_document`,
backed by ``markdown-it-py``), so print/EPUB output cannot drift from the site
renderer: frontmatter and build markers are stripped, tables render as one
``<table>``, lists nest, links and callouts keep their semantics. The exporter
only adds the printable/EPUB shell around the shared renderer.
"""

from __future__ import annotations

import io
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from makewiki_skills.renderer.markdown_render import render_markdown_document

__all__ = [
    "DocExporter",
    "collect_ordered_chapters",
    "parse_export_chapters",
]

# Chapter wrapper of the compiled printable HTML: one section per chapter.
_CHAPTER_OPEN_RE = re.compile(
    r'<section class="chapter" id="([^"]+)">', re.IGNORECASE
)


def parse_export_chapters(html_text: str) -> list[tuple[str, str]]:
    """Split a compiled printable HTML file back into ``(slug, body_html)``.

    The audit endpoint pairs each chapter with its source Markdown; this helper
    lives next to the compiler so the section shell cannot drift away from
    what the audit expects.
    """
    chapters: list[tuple[str, str]] = []
    opens = list(_CHAPTER_OPEN_RE.finditer(html_text))
    for i, m in enumerate(opens):
        # A chapter body runs to the next chapter's open tag, the end of the
        # body container, or the end of the document — whichever comes first.
        if i + 1 < len(opens):
            end = opens[i + 1].start()
        else:
            end = html_text.find("</body>", m.end())
            if end == -1:
                end = len(html_text)
        body = html_text[m.end() : end].strip()
        body = re.sub(r"</section>\s*$", "", body)
        chapters.append((m.group(1), body.strip()))
    return chapters


def render_chapter_html(md: str) -> str:
    """Render one chapter through the shared site renderer (HTML flavor)."""
    return render_markdown_document(md, route_map={})


def render_chapter_xhtml_body(md: str) -> str:
    """Render one chapter body as XHTML for the EPUB archive (self-closed
    void tags keep the OEBPS well-formed XML)."""
    return render_markdown_document(md, route_map={}, xhtml_out=True)


def collect_ordered_chapters(
    makewiki_path: Path, lang: str, default_language: str = "en"
) -> list[tuple[str, str, str]]:
    """Collect and order markdown files for a target language.

    Follows the language-profile filename contract (``LanguageProfile.get_filename``):
    the DEFAULT language's content is the plain ``<base>.md`` while every
    other declared language carries ``.<lang>.md`` — ``en`` is never
    hardcoded.
    """
    suffix = f".{lang}.md" if lang != default_language else ".md"
    standard_order = [
        ("README", "Overview"),
        ("getting-started", "Getting Started"),
        ("installation", "Installation & Deployment"),
        ("configuration", "Configuration Matrix"),
        ("usage/overview", "Usage Overview"),
        ("faq", "Frequently Asked Questions"),
        ("troubleshooting", "Troubleshooting Runbook"),
    ]

    chapters: list[tuple[str, str, str]] = []
    seen_paths: set[str] = set()

    for base, default_title in standard_order:
        target_filename = f"{base}{suffix}"
        p = makewiki_path / target_filename
        if p.is_file():
            content = p.read_text(encoding="utf-8-sig", errors="replace")
            title = _extract_first_h1(content) or default_title
            slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
            chapters.append((title, content, slug))
            seen_paths.add(str(p.resolve()))

    # Collect additional usage/ module files
    usage_dir = makewiki_path / "usage"
    if usage_dir.is_dir():
        for p in sorted(usage_dir.glob(f"*{suffix}")):
            if (
                str(p.resolve()) not in seen_paths
                and p.is_file()
                and not p.name.startswith("overview")
            ):
                content = p.read_text(encoding="utf-8-sig", errors="replace")
                title = _extract_first_h1(content) or p.stem
                slug = f"usage-{p.stem.replace(suffix[:-3], '')}"
                chapters.append((title, content, slug))
                seen_paths.add(str(p.resolve()))

    return chapters


def _extract_first_h1(content: str) -> str | None:
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


class DocExporter:
    """Exports generated MakeWiki markdown documentation into single-file printable HTML and EPUB bundles."""

    def __init__(self, title: str = "Project Documentation") -> None:
        self._title = title

    def export_pdf_ready_html(
        self,
        makewiki_dir: Path,
        lang: str = "en",
        output_file: Path | None = None,
        default_language: str = "en",
    ) -> Path:
        """Compile all documentation chapters for a specific language into a single printable HTML file.

        ``lang`` selects the exported language; ``default_language`` names the
        plain-``.md`` form per the language-profile filename contract (both
        come from the caller's resolved language context — ``en`` is never
        hardcoded).
        """
        makewiki_path = Path(makewiki_dir).resolve()
        export_dir = makewiki_path / "export"
        export_dir.mkdir(parents=True, exist_ok=True)

        if output_file is None:
            filename = (
                f"documentation.{lang}.html"
                if lang != default_language
                else "documentation.html"
            )
            output_file = export_dir / filename

        chapters = collect_ordered_chapters(makewiki_path, lang, default_language)
        rendered_chapters: list[dict[str, str]] = []

        toc_items: list[tuple[str, str]] = []
        for title, raw_md, slug in chapters:
            html = render_chapter_html(raw_md)
            rendered_chapters.append({"title": title, "html": html, "slug": slug})
            toc_items.append((title, slug))

        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        toc_html = "\n".join(f'<li><a href="#{slug}">{title}</a></li>' for title, slug in toc_items)

        chapters_html = "\n".join(
            f'<section class="chapter" id="{ch["slug"]}">\n{ch["html"]}\n</section>'
            for ch in rendered_chapters
        )

        full_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self._title} - Printable PDF Guide</title>
  <style>
    :root {{
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
      --font-mono: "Cascadia Code", "JetBrains Mono", ui-monospace, SFMono-Regular, Consolas, Menlo, monospace;
      --text-color: #334155;
      --heading-color: #0f172a;
      --muted-color: #64748b;
      --faint-color: #94a3b8;
      --border-color: #e2e8f0;
      --border-strong: #cbd5e1;
      --surface: #f8fafc;
      --code-bg: #f1f5f9;
      --accent: #2563eb;
      --accent-hover: #1d4ed8;
      --accent-subtle: #eff6ff;
      --callout-note-bg: #eff6ff;
      --callout-note-border: #3b82f6;
      --callout-warn-bg: #fffbeb;
      --callout-warn-border: #f59e0b;
      --callout-tip-bg: #f0fdf4;
      --callout-tip-border: #22c55e;
      --callout-danger-bg: #fef2f2;
      --callout-danger-border: #ef4444;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-family);
      color: var(--text-color);
      line-height: 1.65;
      padding: 2rem;
      background: #ffffff;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }}
    .print-controls {{
      margin-bottom: 2rem;
      padding: 1rem 1.25rem;
      background: var(--accent-subtle);
      border: 1px solid #bfdbfe;
      border-radius: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }}
    .print-btn {{
      background: var(--accent);
      color: #ffffff;
      border: none;
      padding: 0.6rem 1.4rem;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.95rem;
      font-family: inherit;
      transition: background 0.18s ease, box-shadow 0.18s ease;
    }}
    .print-btn:hover {{ background: var(--accent-hover); }}
    .print-btn:focus-visible {{ outline: 2px solid var(--accent-hover); outline-offset: 2px; }}
    .cover-page {{
      text-align: center;
      padding: 6rem 2rem;
      margin-bottom: 4rem;
      border-bottom: 1px solid var(--border-color);
      page-break-after: always;
      break-after: page;
    }}
    .cover-page h1 {{
      font-size: 2.75rem;
      color: var(--heading-color);
      letter-spacing: -0.02em;
      line-height: 1.2;
      margin-bottom: 1.25rem;
    }}
    .cover-page .accent-rule {{
      width: 56px;
      height: 3px;
      border: 0;
      border-radius: 9999px;
      background: var(--accent);
      margin: 0 auto 1.5rem;
    }}
    .cover-page .subtitle {{
      font-size: 1.2rem;
      color: var(--muted-color);
      margin-bottom: 2.5rem;
      font-weight: 500;
    }}
    .cover-page .meta {{
      font-size: 0.85rem;
      color: var(--faint-color);
      letter-spacing: 0.02em;
    }}
    .toc-section {{
      margin: 3rem 0;
      padding: 1.75rem 2rem;
      background: var(--surface);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      page-break-after: always;
      break-after: page;
    }}
    .toc-section h2 {{
      margin-bottom: 1.25rem;
      color: var(--heading-color);
      font-size: 1.15rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .toc-section ul {{ list-style-type: decimal; padding-left: 1.75rem; }}
    .toc-section li {{ margin-bottom: 0.6rem; }}
    .toc-section li::marker {{ color: var(--faint-color); font-variant-numeric: tabular-nums; }}
    .toc-section a {{ color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent; transition: border-color 0.15s ease, color 0.15s ease; }}
    .toc-section a:hover {{ text-decoration: none; color: var(--accent-hover); border-bottom-color: var(--accent-hover); }}
    .chapter {{
      margin-bottom: 4rem;
      padding-top: 1rem;
      page-break-before: always;
      break-before: page;
    }}
    h1, h2, h3, h4 {{ color: var(--heading-color); margin-top: 1.5rem; margin-bottom: 0.75rem; letter-spacing: -0.015em; line-height: 1.3; }}
    h1 {{ font-size: 2rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
    h2 {{ font-size: 1.5rem; margin-top: 2rem; }}
    h3 {{ font-size: 1.2rem; margin-top: 1.5rem; }}
    p, ul, ol, table, pre {{ margin-bottom: 1.2rem; }}
    ul, ol {{ padding-left: 1.5rem; }}
    li {{ margin-bottom: 0.35rem; }}
    li::marker {{ color: var(--faint-color); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1.5rem 0;
      font-size: 0.9rem;
      font-variant-numeric: tabular-nums;
    }}
    th, td {{ border: 1px solid var(--border-color); padding: 0.6rem 0.8rem; text-align: left; vertical-align: top; }}
    th {{ background: var(--surface); font-weight: 600; }}
    pre {{
      background: var(--code-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1rem;
      overflow-x: auto;
      font-family: var(--font-mono, ui-monospace);
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 0.85rem;
      line-height: 1.6;
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 0.875em;
      background: var(--code-bg);
      border: 1px solid var(--border-color);
      padding: 0.1em 0.35em;
      border-radius: 4px;
    }}
    pre code {{ background: transparent; border: none; padding: 0; }}
    blockquote {{
      border-left: 4px solid var(--callout-note-border, #3b82f6);
      background: var(--callout-note-bg, #eff6ff);
      padding: 0.8rem 1.2rem;
      margin: 1.25rem 0;
      border-radius: 0 8px 8px 0;
      color: var(--text-color);
    }}
    .callout {{ border-left-width: 4px; font-style: normal; }}
    .callout.note {{ border-left-color: var(--callout-note-border, #3b82f6); background: var(--callout-note-bg, #eff6ff); }}
    .callout.tip {{ border-left-color: var(--callout-tip-border, #22c55e); background: var(--callout-tip-bg, #f0fdf4); }}
    .callout.warning {{ border-left-color: var(--callout-warn-border, #f59e0b); background: var(--callout-warn-bg, #fffbeb); }}
    .callout.danger {{ border-left-color: var(--callout-danger-border, #ef4444); background: var(--callout-danger-bg, #fef2f2); }}
    .callout-label {{
      font-weight: 700;
      text-transform: uppercase;
      font-size: 0.75em;
      letter-spacing: 0.05em;
      margin-right: 0.4em;
    }}
    .callout.note .callout-label {{ color: #1d4ed8; }}
    .callout.tip .callout-label {{ color: #15803d; }}
    .callout.warning .callout-label {{ color: #b45309; }}
    .callout.danger .callout-label {{ color: #b91c1c; }}
    img {{ max-width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--border-color); }}
    hr {{ border: 0; border-top: 1px solid var(--border-color); margin: 2rem 0; }}
    @media print {{
      body {{ padding: 0; font-size: 11pt; }}
      .print-controls {{ display: none; }}
      .cover-page {{ padding-top: 4rem; }}
      .chapter {{ page-break-before: always; break-before: page; }}
      pre, table, blockquote {{ page-break-inside: avoid; break-inside: avoid; }}
      a {{ color: inherit; text-decoration: none; }}
      th {{ background: #f1f5f9 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}
</head>
<body>
  <div class="print-controls">
    <div><strong>Ready for Export:</strong> Click the button to print or save as a single PDF document.</div>
    <button class="print-btn" onclick="window.print()">Print to PDF</button>
  </div>

  <div class="cover-page">
    <h1>{self._title}</h1>
    <div class="subtitle">Complete Technical Guide and Enterprise Operations Manual</div>
    <div class="meta">Generated by MakeWiki.skills &bull; {now_str} &bull; Language: {lang}</div>
  </div>

  <div class="toc-section">
    <h2>Table of Contents</h2>
    <ul>
      {toc_html}
    </ul>
  </div>

  <div class="content-container">
    {chapters_html}
  </div>
</body>
</html>
"""
        output_file.write_text(full_html, encoding="utf-8")
        return output_file

    def export_epub(
        self,
        makewiki_dir: Path,
        lang: str = "en",
        output_file: Path | None = None,
        default_language: str = "en",
    ) -> Path:
        """Compile documentation into a standard, valid EPUB e-book archive.

        ``lang`` selects the exported language; ``default_language`` names the
        plain-``.md`` form per the language-profile filename contract.
        """
        makewiki_path = Path(makewiki_dir).resolve()
        export_dir = makewiki_path / "export"
        export_dir.mkdir(parents=True, exist_ok=True)

        if output_file is None:
            filename = (
                f"documentation.{lang}.epub"
                if lang != default_language
                else "documentation.epub"
            )
            output_file = export_dir / filename

        chapters = collect_ordered_chapters(makewiki_path, lang, default_language)
        book_uuid = str(uuid.uuid4())
        date_str = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as epub:
            # 1. mimetype (must be uncompressed and first)
            epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

            # 2. META-INF/container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
            epub.writestr("META-INF/container.xml", container_xml)

            # 3. Chapters
            manifest_items: list[str] = []
            spine_items: list[str] = []
            nav_points: list[str] = []

            for idx, (title, raw_md, slug) in enumerate(chapters, start=1):
                html_body = render_chapter_xhtml_body(raw_md)
                chapter_xhtml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="{lang}">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <h1>{title}</h1>
  {html_body}
</body>
</html>"""
                ch_filename = f"chapter_{idx:02d}_{slug}.xhtml"
                epub.writestr(f"OEBPS/{ch_filename}", chapter_xhtml)

                item_id = f"ch_{idx:02d}"
                manifest_items.append(
                    f'<item id="{item_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>'
                )
                spine_items.append(f'<itemref idref="{item_id}"/>')
                nav_points.append(f"""    <navPoint id="navPoint-{idx}" playOrder="{idx}">
      <navLabel><text>{title}</text></navLabel>
      <content src="{ch_filename}"/>
    </navPoint>""")

            # 4. CSS
            epub_css = """body { font-family: sans-serif; line-height: 1.5; padding: 5%; }
h1, h2, h3 { color: #0f172a; margin-top: 1.2em; margin-bottom: 0.6em; }
h1 { font-size: 1.8em; border-bottom: 1px solid #cbd5e1; }
pre { background: #f1f5f9; padding: 0.8em; font-family: monospace; font-size: 0.9em; overflow-x: auto; }
code { font-family: monospace; background: #f1f5f9; padding: 0.1em 0.3em; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #cbd5e1; padding: 0.5em; text-align: left; }
th { background: #f8fafc; font-weight: bold; }
blockquote { border-left: 3px solid #3b82f6; background: #eff6ff; padding: 0.5em 1em; margin: 1em 0; }
.callout-label { font-weight: bold; }"""
            epub.writestr("OEBPS/style.css", epub_css)

            # 5. content.opf
            content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookID" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{self._title}</dc:title>
    <dc:language>{lang}</dc:language>
    <dc:identifier id="BookID" opf:scheme="UUID">{book_uuid}</dc:identifier>
    <dc:creator>MakeWiki.skills</dc:creator>
    <dc:date>{date_str}</dc:date>
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="style" href="style.css" media-type="text/css"/>
    {chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx">
    {chr(10).join(spine_items)}
  </spine>
</package>"""
            epub.writestr("OEBPS/content.opf", content_opf)

            # 6. toc.ncx
            toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z398/2005/ncx" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{book_uuid}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{self._title}</text></docTitle>
  <navMap>
{chr(10).join(nav_points)}
  </navMap>
</ncx>"""
            epub.writestr("OEBPS/toc.ncx", toc_ncx)

        output_file.write_bytes(zip_buffer.getvalue())
        return output_file
