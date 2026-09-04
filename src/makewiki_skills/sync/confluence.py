"""Confluence Storage Format exporter and Space sync tool."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any


class ConfluenceConverter:
    """Converts Markdown documents into Atlassian Confluence Storage Format (XHTML)."""

    def to_storage_format(self, markdown: str) -> str:
        """Convert standard markdown into Confluence Storage Format XML."""
        xml_lines: list[str] = []
        lines = markdown.splitlines()
        in_code = False
        code_lang = ""
        code_lines: list[str] = []

        for line in lines:
            # Code fences
            fence_match = re.match(r"^```(\w*)\s*$", line.strip())
            if fence_match:
                if in_code:
                    code_content = "\n".join(code_lines)
                    xml_lines.append(
                        f'<ac:structured-macro ac:name="code">'
                        f'<ac:parameter ac:name="language">{code_lang or "bash"}</ac:parameter>'
                        f"<ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body>"
                        f"</ac:structured-macro>"
                    )
                    in_code = False
                    code_lines = []
                else:
                    in_code = True
                    code_lang = fence_match.group(1).lower()
                    code_lines = []
                continue

            if in_code:
                code_lines.append(line)
                continue

            stripped = line.strip()
            if not stripped:
                continue

            # Headings
            h_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if h_match:
                level = len(h_match.group(1))
                heading_text = html.escape(h_match.group(2))
                xml_lines.append(f"<h{level}>{heading_text}</h{level}>")
                continue

            # Blockquotes / Info callouts
            if stripped.startswith(">"):
                quote_text = html.escape(stripped.lstrip("> ").strip())
                macro_name = (
                    "warning" if "注意" in quote_text or "Warning" in quote_text else "info"
                )
                xml_lines.append(
                    f'<ac:structured-macro ac:name="{macro_name}">'
                    f"<ac:rich-text-body><p>{quote_text}</p></ac:rich-text-body>"
                    f"</ac:structured-macro>"
                )
                continue

            # Tables
            if stripped.startswith("|") and stripped.endswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if all(re.match(r"^:?-+:?$", c) for c in cells):
                    continue
                row_xml = "".join(f"<td>{html.escape(c)}</td>" for c in cells)
                xml_lines.append(f"<table><tbody><tr>{row_xml}</tr></tbody></table>")
                continue

            # Regular Paragraph
            escaped_text = html.escape(stripped)
            # Inline code
            escaped_text = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped_text)
            # Bold
            escaped_text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped_text)
            xml_lines.append(f"<p>{escaped_text}</p>")

        if in_code and code_lines:
            code_content = "\n".join(code_lines)
            xml_lines.append(
                f'<ac:structured-macro ac:name="code">'
                f'<ac:parameter ac:name="language">{code_lang or "bash"}</ac:parameter>'
                f"<ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body>"
                f"</ac:structured-macro>"
            )

        return "\n".join(xml_lines)


class ConfluenceSyncTool:
    """Manages bundle creation and synchronization with Confluence Server / Cloud."""

    def __init__(self) -> None:
        self._converter = ConfluenceConverter()

    def build_sync_bundle(
        self,
        makewiki_dir: Path,
        space_key: str = "WIKI",
        lang: str = "en",
        default_language: str = "en",
    ) -> Path:
        """Compile documentation into Confluence Storage XML pages ready for API sync.

        Follows the language-profile filename contract: the DEFAULT language's
        content is the plain ``<base>.md`` while every other declared language
        carries ``.<lang>.md``. ``lang`` selects which language's pages go into
        the bundle; ``default_language`` names the plain-``.md`` form (both
        come from the caller's resolved language context — ``en`` is never
        hardcoded).
        """
        makewiki_path = Path(makewiki_dir).resolve()
        sync_dir = makewiki_path / "sync" / "confluence" / lang
        sync_dir.mkdir(parents=True, exist_ok=True)

        suffix = f".{lang}.md" if lang != default_language else ".md"
        pages: list[dict[str, Any]] = []

        for p in makewiki_path.rglob("*.md"):
            if lang != default_language and not p.name.endswith(suffix):
                continue
            if lang == default_language and "." in p.name[:-3]:
                continue
            if "export" in p.parts or "sync" in p.parts or "site" in p.parts:
                continue

            raw_md = p.read_text(encoding="utf-8", errors="replace")
            title_match = re.search(r"^#\s+(.+)$", raw_md, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else p.stem

            storage_xml = self._converter.to_storage_format(raw_md)
            page_id = p.stem.replace(suffix[:-3], "") or "index"
            xml_file = sync_dir / f"{page_id}.xml"
            xml_file.write_text(storage_xml, encoding="utf-8")

            pages.append(
                {
                    "id": page_id,
                    "title": title,
                    "space_key": space_key,
                    "xml_file": str(xml_file.relative_to(makewiki_path)),
                    "parent_id": None if page_id in ("README", "index") else "README",
                }
            )

        manifest = {
            "space_key": space_key,
            "language": lang,
            "total_pages": len(pages),
            "pages": pages,
        }
        (sync_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return sync_dir
