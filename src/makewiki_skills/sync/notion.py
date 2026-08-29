"""Notion API Block object converter and workspace sync tool."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class NotionBlockConverter:
    """Converts Markdown documents into Notion Block API payloads."""

    def to_notion_blocks(self, markdown: str) -> list[dict[str, Any]]:
        """Convert standard markdown into a list of Notion block objects."""
        blocks: list[dict[str, Any]] = []
        lines = markdown.splitlines()
        in_code = False
        code_lang = ""
        code_lines: list[str] = []

        for line in lines:
            fence_match = re.match(r"^```(\w*)\s*$", line.strip())
            if fence_match:
                if in_code:
                    blocks.append(
                        {
                            "object": "block",
                            "type": "code",
                            "code": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": "\n".join(code_lines)}}
                                ],
                                "language": code_lang or "plain text",
                            },
                        }
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
            h_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
            if h_match:
                level = len(h_match.group(1))
                h_type = f"heading_{level}"
                text = h_match.group(2)
                blocks.append(
                    {
                        "object": "block",
                        "type": h_type,
                        h_type: {
                            "rich_text": [{"type": "text", "text": {"content": text}}],
                        },
                    }
                )
                continue

            # Callout
            if stripped.startswith(">"):
                quote_text = stripped.lstrip("> ").strip()
                blocks.append(
                    {
                        "object": "block",
                        "type": "callout",
                        "callout": {
                            "rich_text": [{"type": "text", "text": {"content": quote_text}}],
                            "icon": {"emoji": "💡"},
                        },
                    }
                )
                continue

            # Bulleted List
            if stripped.startswith("- ") or stripped.startswith("* "):
                item_text = stripped[2:].strip()
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": item_text}}],
                        },
                    }
                )
                continue

            # Paragraph
            blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": stripped}}],
                    },
                }
            )

        if in_code and code_lines:
            blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                        "language": code_lang or "plain text",
                    },
                }
            )

        return blocks


class NotionSyncTool:
    """Manages bundle creation and synchronization with Notion API."""

    def __init__(self) -> None:
        self._converter = NotionBlockConverter()

    def build_sync_bundle(
        self,
        makewiki_dir: Path,
        parent_page_id: str = "root",
        lang: str = "en",
    ) -> Path:
        """Compile documentation into Notion Block API payloads ready for import/sync."""
        makewiki_path = Path(makewiki_dir).resolve()
        sync_dir = makewiki_path / "sync" / "notion" / lang
        sync_dir.mkdir(parents=True, exist_ok=True)

        suffix = f".{lang}.md" if lang != "en" else ".md"
        pages: list[dict[str, Any]] = []

        for p in makewiki_path.rglob("*.md"):
            if lang != "en" and not p.name.endswith(suffix):
                continue
            if lang == "en" and "." in p.name[:-3]:
                continue
            if "export" in p.parts or "sync" in p.parts or "site" in p.parts:
                continue

            raw_md = p.read_text(encoding="utf-8", errors="replace")
            title_match = re.search(r"^#\s+(.+)$", raw_md, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else p.stem

            blocks = self._converter.to_notion_blocks(raw_md)
            page_id = p.stem.replace(suffix[:-3], "") or "index"

            payload = {
                "parent": {"page_id": parent_page_id},
                "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}},
                "children": blocks,
            }

            json_file = sync_dir / f"{page_id}.json"
            json_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            pages.append(
                {
                    "id": page_id,
                    "title": title,
                    "json_file": str(json_file.relative_to(makewiki_path)),
                    "total_blocks": len(blocks),
                }
            )

        manifest = {
            "parent_page_id": parent_page_id,
            "language": lang,
            "total_pages": len(pages),
            "pages": pages,
        }
        (sync_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return sync_dir
