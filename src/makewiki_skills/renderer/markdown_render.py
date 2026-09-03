"""Server-side Markdown -> HTML rendering for the MakeWiki static site.

This module is the *mechanical* Markdown renderer. It converts the LLM-authored
Markdown documents into HTML at build time, using the mature CommonMark
implementation ``markdown-it-py``. The browser then just injects this
pre-rendered HTML instead of re-parsing Markdown client-side.

Responsibilities:
- Render CommonMark plus tables and strikethrough.
- Attach stable, github-style ``id`` attributes to headings so in-page
  ``#section`` anchors have a real target, independent of document routes.
- Rewrite link ``href`` values so that internal ``.md`` links resolve to SPA
  routes, external links open safely, and in-page anchors are flagged.

The caller (``site_compiler``) is responsible for script-safety of the emitted
HTML and for the offline single-file bundle.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, cast

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

__all__ = ["slugify", "render_markdown_document"]

# One shared parser per document: CommonMark plus tables and strikethrough.
# The ``gfm-like`` preset is intentionally avoided because it enables linkify,
# whose ``linkify-it-py`` dependency is not installed.
_PARSER = MarkdownIt("commonmark").enable(["table", "strikethrough"])

# A single reusable token renderer for the small set of overridden rules. Rule
# functions are invoked unbound as ``rules[type](tokens, i, options, env)``, so
# they carry no ``self``; we delegate tag emission to a real ``RendererHTML``.
_RENDERER = RendererHTML()

# markdown-it-py types ``MarkdownIt.renderer`` as a narrow ``RendererProtocol``
# that hides the ``rules`` table; the concrete renderer is a ``RendererHTML``.
_RENDERER_RULES: dict[str, Any] = cast(RendererHTML, _PARSER.renderer).rules

_NON_WORD = re.compile(r"[^\w\s-]")
_SPACES = re.compile(r"[\s_]+")


def slugify(text: str) -> str:
    """Return a github-style slug for ``text`` (lowercase, ``-`` separated).

    Non-ASCII characters are removed, so a CJK heading falls back to a stable
    empty-safe segment; an empty result becomes ``"section"``.
    """
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = _SPACES.sub("-", _NON_WORD.sub("", ascii_text).lower()).strip("-")
    return slug or "section"


def _heading_open(tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType) -> str:
    """Attach a stable id to headings, de-duplicated within one document."""
    token = tokens[idx]
    inline = tokens[idx + 1] if idx + 1 < len(tokens) else None
    heading_text = inline.content if inline is not None else ""
    slug = slugify(heading_text)
    seen: set[str] = env.setdefault("heading_ids", set())
    if slug in seen:
        suffix = 2
        candidate = f"{slug}-{suffix}"
        while candidate in seen:
            suffix += 1
            candidate = f"{slug}-{suffix}"
        slug = candidate
    seen.add(slug)
    token.attrSet("id", slug)
    return _RENDERER.renderToken(tokens, idx, options, env)


def _link_open(tokens: Sequence[Token], idx: int, options: OptionsDict, env: EnvType) -> str:
    """Classify links and rewrite internal ``.md`` hrefs into SPA routes."""
    token = tokens[idx]
    href = str(token.attrGet("href") or "")
    route_map: Mapping[str, str] = env.get("route_map", {})
    if href.startswith(("http://", "https://", "mailto:")):
        token.attrSet("class", "external-link")
        token.attrSet("target", "_blank")
        token.attrSet("rel", "noopener")
    elif href.startswith("#"):
        # In-page anchor: leave the browser to scroll to the heading id.
        token.attrSet("class", "anchor-link")
    else:
        # Internal wiki link. Normalize a Markdown-ish href into a route.
        normalized = href.lstrip("./")
        fragment = ""
        if "#" in normalized:
            normalized, fragment = normalized.split("#", 1)
        if normalized.endswith(".md"):
            normalized = normalized[: -len(".md")]
        route: str | None = None
        if normalized:
            lookup = normalized.lower()
            for doc_id, doc_route in route_map.items():
                if doc_id.lower() == lookup:
                    route = doc_route
                    break
        if route is not None:
            target = "#" + (route if route.startswith("/") else "/" + route)
            token.attrSet("href", target)
            token.attrSet("class", "wiki-link")
            if fragment:
                token.attrSet("data-anchor", fragment)
        # Unknown internal link: leave href untouched (renders, no crash).
    return _RENDERER.renderToken(tokens, idx, options, env)


_RENDERER_RULES["heading_open"] = _heading_open
_RENDERER_RULES["link_open"] = _link_open

# A deterministic callout convention: a blockquote whose first paragraph begins
# with a bracketed keyword is rendered as a typed callout (note/tip/warning/
# danger) with an accessible type label. The type is authored by the LLM in the
# Markdown; this transform is purely mechanical (a documented syntax -> class),
# never a semantic judgment about the content.
_CALLOUT_RE = re.compile(
    r"<blockquote>\s*<p>\s*\[!(\s*)(NOTE|TIP|WARNING|DANGER)(\s*)\]\s*", re.IGNORECASE
)
_CALLOUT_LABELS = {
    "NOTE": "Note",
    "TIP": "Tip",
    "WARNING": "Warning",
    "DANGER": "Danger",
}


def _apply_callouts(html: str) -> str:
    """Turn ``> [!TYPE]`` blockquotes into typed callouts, leaving plain
    blockquotes untouched, so a quote is never stylistically confused with an
    admonition."""
    out: list[str] = []
    last = 0
    for m in _CALLOUT_RE.finditer(html):
        out.append(html[last : m.start()])
        kind = m.group(2).upper()
        label = _CALLOUT_LABELS[kind]
        # Rewrite the opening: blockquote gets the callout class, a labelled
        # span is inserted before the remaining paragraph text (marker dropped).
        out.append(
            f'<blockquote class="callout {kind.lower()}"><p>'
            f'<span class="callout-label">{label}</span>'
        )
        last = m.end()
    out.append(html[last:])
    return "".join(out)


_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n?", re.DOTALL)


def render_markdown_document(md: str, *, route_map: Mapping[str, str]) -> str:
    """Render one Markdown document to HTML, resolving wiki links against
    ``route_map`` (a mapping of document id -> route) and re-seeding heading ids
    per call."""
    # Strip a leading YAML frontmatter block: it is metadata, not content, and
    # markdown-it would otherwise render the `---` fences as thematic breaks and
    # the `key: value` lines as paragraphs.
    md = _FRONTMATTER_RE.sub("", md, count=1)
    env: EnvType = {"route_map": route_map, "heading_ids": set()}
    rendered = cast(str, _PARSER.render(md, env))
    return _apply_callouts(rendered)
