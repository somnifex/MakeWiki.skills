"""Single-file documentation exporters for PDF-ready HTML, EPUB, and offline printable bundles."""

from __future__ import annotations

import html
import io
import re
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path


class SimpleMarkdownRenderer:
    """Converts Markdown text into clean, printable HTML."""

    def to_html(self, markdown: str) -> str:
        html_lines: list[str] = []
        lines = markdown.splitlines()
        in_code = False
        code_lines: list[str] = []

        for line in lines:
            fence_match = re.match(r"^```(\w*)\s*$", line.strip())
            if fence_match:
                if in_code:
                    escaped_code = html.escape("\n".join(code_lines))
                    html_lines.append(f"<pre><code>{escaped_code}</code></pre>")
                    in_code = False
                    code_lines = []
                else:
                    in_code = True
                    code_lines = []
                continue

            if in_code:
                code_lines.append(line)
                continue

            stripped = line.strip()
            if not stripped:
                continue

            h_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if h_match:
                lvl = len(h_match.group(1))
                h_text = html.escape(h_match.group(2))
                html_lines.append(f"<h{lvl}>{h_text}</h{lvl}>")
                continue

            if stripped.startswith(">"):
                q_text = html.escape(stripped.lstrip("> ").strip())
                html_lines.append(f"<blockquote><p>{q_text}</p></blockquote>")
                continue

            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if all(re.match(r"^:?-+:?$", c) for c in cells):
                    continue
                row_html = "".join(f"<td>{html.escape(c)}</td>" for c in cells)
                html_lines.append(f"<table><tbody><tr>{row_html}</tr></tbody></table>")
                continue

            if stripped.startswith("- ") or stripped.startswith("* "):
                item = html.escape(stripped[2:].strip())
                item = re.sub(r"`([^`]+)`", r"<code>\1</code>", item)
                item = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", item)
                html_lines.append(f"<ul><li>{item}</li></ul>")
                continue

            escaped = html.escape(stripped)
            escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
            escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
            html_lines.append(f"<p>{escaped}</p>")

        if in_code and code_lines:
            escaped_code = html.escape("\n".join(code_lines))
            html_lines.append(f"<pre><code>{escaped_code}</code></pre>")

        return "\n".join(html_lines)


class DocExporter:
    """Exports generated MakeWiki markdown documentation into single-file printable HTML and EPUB bundles."""

    def __init__(self, title: str = "Project Documentation") -> None:
        self._title = title
        self._md = SimpleMarkdownRenderer()

    def export_pdf_ready_html(
        self,
        makewiki_dir: Path,
        lang: str = "en",
        output_file: Path | None = None,
    ) -> Path:
        """Compile all documentation chapters for a specific language into a single printable HTML file."""
        makewiki_path = Path(makewiki_dir).resolve()
        export_dir = makewiki_path / "export"
        export_dir.mkdir(parents=True, exist_ok=True)

        if output_file is None:
            filename = f"documentation.{lang}.html" if lang != "en" else "documentation.html"
            output_file = export_dir / filename

        chapters = self._collect_ordered_chapters(makewiki_path, lang)
        rendered_chapters: list[dict[str, str]] = []

        toc_items: list[tuple[str, str]] = []
        for title, raw_md, slug in chapters:
            html = self._md.to_html(raw_md)
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
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      --text-color: #1e293b;
      --heading-color: #0f172a;
      --border-color: #cbd5e1;
      --code-bg: #f1f5f9;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-family);
      color: var(--text-color);
      line-height: 1.6;
      padding: 2rem;
      background: #ffffff;
    }}
    .print-controls {{
      margin-bottom: 2rem;
      padding: 1rem;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .print-btn {{
      background: #2563eb;
      color: #ffffff;
      border: none;
      padding: 0.6rem 1.2rem;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.95rem;
    }}
    .print-btn:hover {{ background: #1d4ed8; }}
    .cover-page {{
      text-align: center;
      padding: 6rem 2rem;
      margin-bottom: 4rem;
      border-bottom: 2px solid var(--border-color);
      page-break-after: always;
      break-after: page;
    }}
    .cover-page h1 {{
      font-size: 2.75rem;
      color: var(--heading-color);
      margin-bottom: 1rem;
    }}
    .cover-page .subtitle {{
      font-size: 1.25rem;
      color: #64748b;
      margin-bottom: 2rem;
    }}
    .cover-page .meta {{
      font-size: 0.9rem;
      color: #94a3b8;
    }}
    .toc-section {{
      margin: 3rem 0;
      padding: 1.5rem;
      background: #f8fafc;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      page-break-after: always;
      break-after: page;
    }}
    .toc-section h2 {{ margin-bottom: 1rem; color: var(--heading-color); }}
    .toc-section ul {{ list-style-type: decimal; padding-left: 2rem; }}
    .toc-section li {{ margin-bottom: 0.5rem; }}
    .toc-section a {{ color: #2563eb; text-decoration: none; }}
    .toc-section a:hover {{ text-decoration: underline; }}
    .chapter {{
      margin-bottom: 4rem;
      padding-top: 1rem;
      page-break-before: always;
      break-before: page;
    }}
    h1, h2, h3, h4 {{ color: var(--heading-color); margin-top: 1.5rem; margin-bottom: 0.75rem; }}
    h1 {{ font-size: 2rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
    h2 {{ font-size: 1.5rem; }}
    h3 {{ font-size: 1.2rem; }}
    p, ul, ol, table, pre {{ margin-bottom: 1.2rem; }}
    ul, ol {{ padding-left: 1.5rem; }}
    li {{ margin-bottom: 0.3rem; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; font-size: 0.9rem; }}
    th, td {{ border: 1px solid var(--border-color); padding: 0.6rem 0.8rem; text-align: left; }}
    th {{ background: #f8fafc; font-weight: 600; }}
    pre {{
      background: var(--code-bg);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 1rem;
      overflow-x: auto;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 0.85rem;
      page-break-inside: avoid;
      break-inside: avoid;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 0.875em;
      background: var(--code-bg);
      padding: 0.2em 0.4em;
      border-radius: 4px;
    }}
    blockquote {{
      border-left: 4px solid #3b82f6;
      background: #eff6ff;
      padding: 0.8rem 1.2rem;
      margin: 1rem 0;
      border-radius: 0 6px 6px 0;
    }}
    @media print {{
      body {{ padding: 0; font-size: 11pt; }}
      .print-controls {{ display: none; }}
      .chapter {{ page-break-before: always; break-before: page; }}
      pre, table, blockquote {{ page-break-inside: avoid; break-inside: avoid; }}
      a {{ color: inherit; text-decoration: none; }}
    }}
  </style>
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
    ) -> Path:
        """Compile documentation into a standard, valid EPUB e-book archive."""
        makewiki_path = Path(makewiki_dir).resolve()
        export_dir = makewiki_path / "export"
        export_dir.mkdir(parents=True, exist_ok=True)

        if output_file is None:
            filename = f"documentation.{lang}.epub" if lang != "en" else "documentation.epub"
            output_file = export_dir / filename

        chapters = self._collect_ordered_chapters(makewiki_path, lang)
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
                html_body = self._md.to_html(raw_md)
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
blockquote { border-left: 3px solid #3b82f6; background: #eff6ff; padding: 0.5em 1em; margin: 1em 0; }"""
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
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
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

    def _collect_ordered_chapters(
        self, makewiki_path: Path, lang: str
    ) -> list[tuple[str, str, str]]:
        """Collect and order markdown files for a target language."""
        suffix = f".{lang}.md" if lang != "en" else ".md"
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
                content = p.read_text(encoding="utf-8", errors="replace")
                title = self._extract_first_h1(content) or default_title
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
                    content = p.read_text(encoding="utf-8", errors="replace")
                    title = self._extract_first_h1(content) or p.stem
                    slug = f"usage-{p.stem.replace(suffix[:-3], '')}"
                    chapters.append((title, content, slug))
                    seen_paths.add(str(p.resolve()))

        return chapters

    @staticmethod
    def _extract_first_h1(content: str) -> str | None:
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None
