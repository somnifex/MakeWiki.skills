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

from makewiki_skills.review.section_parser import SECTION_MARKER_LINE
from makewiki_skills.toolkit.filesystem import strip_ref_prefix

__all__ = ["slugify", "strip_build_metadata", "render_markdown_document"]

# One shared parser per XHTML mode: CommonMark plus tables and strikethrough.
# The ``gfm-like`` preset is intentionally avoided because it enables linkify,
# whose ``linkify-it-py`` dependency is not installed. Built lazily so the
# module import stays cheap and the custom rules below are already defined.

# A single reusable token renderer for the small set of overridden rules. Rule
# functions are invoked unbound as ``rules[type](tokens, i, options, env)``, so
# they carry no ``self``; we delegate tag emission to a real ``RendererHTML``.
_RENDERER = RendererHTML()

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
        # Links address documents by id, not by filesystem path: leading ./ or
        # ../ segments are dropped, while a leading dot that starts a real
        # filename (e.g. ".env.example") is preserved by strip_ref_prefix.
        normalized = strip_ref_prefix(href)
        while normalized.startswith("../"):
            normalized = normalized[3:]
        normalized = normalized.lstrip("/")
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

# --- build-metadata marker hygiene -------------------------------------------
# The verification plane authors three marker families into the Markdown:
# stable code-block IDs ([[id:<slug>]]), parity exemptions ([[parity:ignore
# ...]]) and stable section markers (<!-- makewiki:section=<id> -->). They are
# pipeline metadata consumed by the L4/parity tooling, never reader-facing
# content, so the renderer drops WHOLE-LINE occurrences before parsing. The
# line grammars mirror the authoritative patterns in
# ``verification/l4_cross_language.py`` (block ids) and
# ``review/section_parser.py`` (section markers).
_MARKER_LINE_RE = re.compile(
    r"^\s*(?:"
    r"\[\[id:[A-Za-z0-9_.\-]+\]\]"
    r"|\[\[parity:ignore[^\]]*\]\]"
    r")\s*$"
)
# Fence OPENING line: up to three leading spaces, 3+ fence chars, then any
# info string. The closing line is only the fence character repeated.
_FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def strip_build_metadata(md: str) -> str:
    """Remove build-metadata marker lines from one Markdown document.

    Outside a fence a marker occupies its own line, so the line is dropped
    (otherwise markdown-it renders it as a visible paragraph). Inside a fence
    only the leading marker lines — the documented first-line position of a
    stable block ID — are dropped; a marker further inside code content is
    left alone and the rendered-output audit flags it instead, so this
    mechanical transform never rewrites real code semantics.
    """
    out: list[str] = []
    fence: str | None = None  # the opening fence token (``` or ~~~)
    at_fence_head = False  # inside the documented marker position of a fence
    for line in md.splitlines():
        if fence is not None:
            if re.fullmatch(rf"\s{{0,3}}{re.escape(fence[0])}{{3,}}\s*", line):
                fence = None
                out.append(line)
                continue
            if at_fence_head and _MARKER_LINE_RE.match(line):
                continue
            at_fence_head = False
            out.append(line)
            continue
        fence_match = _FENCE_OPEN_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            at_fence_head = True
            out.append(line)
            continue
        if _MARKER_LINE_RE.match(line) or SECTION_MARKER_LINE.match(line):
            continue
        out.append(line)
    return "\n".join(out)


def _build_parser(*, xhtml: bool) -> MarkdownIt:
    """One parser per XHTML mode with the shared custom render rules."""
    parser = MarkdownIt("commonmark").enable(["table", "strikethrough"])
    if xhtml:
        # EPUB chapters are XHTML; self-close void elements so the archive
        # stays well-formed XML.
        parser.options.update({"xhtmlOut": True})
    rules = cast(RendererHTML, parser.renderer).rules
    rules["heading_open"] = _heading_open
    rules["link_open"] = _link_open
    return parser


_PARSER = _build_parser(xhtml=False)
_PARSER_XHTML = _build_parser(xhtml=True)


def render_markdown_document(
    md: str, *, route_map: Mapping[str, str], xhtml_out: bool = False
) -> str:
    """Render one Markdown document to HTML, resolving wiki links against
    ``route_map`` (a mapping of document id -> route) and re-seeding heading ids
    per call. A leading YAML frontmatter block is stripped (metadata, not
    content), as are whole-line build markers. ``xhtml_out=True`` emits
    XHTML-style void tags for XML consumers such as EPUB."""
    md = _FRONTMATTER_RE.sub("", md, count=1)
    md = strip_build_metadata(md)
    env: EnvType = {"route_map": route_map, "heading_ids": set()}
    parser = _PARSER_XHTML if xhtml_out else _PARSER
    rendered = cast(str, parser.render(md, env))
    return _apply_callouts(rendered)
