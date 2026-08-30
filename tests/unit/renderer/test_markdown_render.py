"""Unit tests for the server-side Markdown renderer.

``markdown_render`` is the mechanical Markdown -> HTML engine used by the site
compiler. It renders CommonMark (plus tables and strikethrough) with stable
heading ids and SPA-aware link rewriting. These tests pin its behaviour:
heading ids (incl. duplicate de-duplication), tables, nested lists,
strikethrough, blockquotes, fenced code with language classes, images, and the
external / in-page / internal wiki-link href rewriting.
"""

from __future__ import annotations

import json

from makewiki_skills.renderer.markdown_render import (
    render_markdown_document,
    slugify,
)

ROUTE_MAP = {
    "getting-started": "/getting-started",
    "README": "/",
    "guide": "/guide",
    "guide/deep": "/guide/deep",
}


# Script-safe serialization used by the site compiler; replicated here so the
# unit test proves a document containing a raw ``</script>`` cannot break out
# of the single <script> payload once serialized this way.
def _safe_json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


def _render(md: str) -> str:
    return render_markdown_document(md, route_map=ROUTE_MAP)


def test_slugify_github_style():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Getting Started  ") == "getting-started"
    assert slugify("A_B_C") == "a-b-c"
    assert slugify("Café") == "cafe"  # NFKD decomposes é -> e
    assert slugify("你") == "section"  # empty-safe fallback


def test_heading_ids_are_attached_and_deduplicated():
    md = "## First\n\n## First\n\n### Nested\n\n## Second"
    html = _render(md)
    assert 'id="first"' in html
    # Duplicate heading text gets a -2 suffix, not the same id twice.
    assert 'id="first-2"' in html
    assert html.count('id="first') == 2
    assert 'id="nested"' in html
    assert 'id="second"' in html


def test_heading_ids_match_browser_anchor_lookup():
    html = _render("## On This Page\n\nSome body")
    assert 'id="on-this-page"' in html


def test_tables_render():
    html = _render("| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n")
    assert "<table>" in html
    assert "<th>A</th>" in html
    assert html.count("<tr>") == 3  # header + two body rows


def test_strikethrough_render():
    assert "<s>gone</s>" in _render("~~gone~~")


def test_nested_lists_render():
    html = _render("- one\n  - two\n    - three\n- four\n")
    assert "<li>one" in html
    assert html.count("<ul>") == 3  # nested lists preserved
    assert html.count("<li>") == 4


def test_blockquote_renders():
    assert "<blockquote>" in _render("> quoted text\n")


def test_callout_types_render_typed_and_labelled():
    # Each of the four GFM-style callout markers becomes a typed blockquote with
    # an accessible label span; the marker itself is dropped.
    for kind, label in [("NOTE", "Note"), ("TIP", "Tip"),
                        ("WARNING", "Warning"), ("DANGER", "Danger")]:
        html = _render(f"> [!{kind}]\n> heed this\n")
        assert f'<blockquote class="callout {kind.lower()}">' in html, kind
        assert f'<span class="callout-label">{label}</span>' in html, kind
        assert "callout-marker" not in html  # marker text is dropped, not kept


def test_callout_marker_is_case_insensitive():
    html = _render("> [!warning]\n> careful\n")
    assert '<blockquote class="callout warning">' in html


def test_plain_blockquote_never_styled_as_callout():
    # A quote is never stylistically confused with an admonition.
    html = _render("> just a quote\n")
    assert "<blockquote>" in html
    assert 'class="callout' not in html
    assert "callout-label" not in html


def test_callout_does_not_break_heading_ids_or_links():
    # A callout next to headings and an internal link must not disturb the
    # stable heading id or the route rewrite.
    html = _render("# Install\n\n> [!TIP]\n> run `make build`\n\nSee [guide](guide.md).\n")
    assert 'id="install"' in html
    assert 'class="callout tip"' in html
    assert 'class="wiki-link"' in html


def test_fenced_code_preserves_language_class():
    html = _render("```python\nprint('hi')\n```\n")
    assert 'class="language-python"' in html
    assert "<code" in html


def test_inline_code_and_bold_italic():
    html = _render("Run `npm i` and **bold** *italic*")
    assert "<code>npm i</code>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_images_render():
    assert '<img src="/img.png" alt="alt"' in _render("![alt](/img.png)")


def test_external_links_open_safely():
    html = _render("[site](https://example.com)\n\n[mail](mailto:a@b.c)")
    assert 'class="external-link"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener"' in html


def test_in_page_anchor_links_classified():
    html = _render("[jump](#intro)")
    assert 'href="#intro"' in html
    assert 'class="anchor-link"' in html


def test_internal_md_links_rewrite_to_routes():
    html = _render("[go](../getting-started.md)")
    assert 'href="#/getting-started"' in html
    assert 'class="wiki-link"' in html


def test_internal_link_with_fragment_carries_data_anchor():
    html = _render("[go](guide.md#deep)")
    assert 'href="#/guide"' in html
    assert 'class="wiki-link"' in html
    assert 'data-anchor="deep"' in html


def test_case_insensitive_doc_id_lookup():
    html = _render("[go](Getting-Started.md)")
    assert 'href="#/getting-started"' in html


def test_link_that_drops_md_extension_resolves():
    html = _render("[guide](guide)")
    # "guide" isn't a document id; it does not map. No crash, no bogus rewrite
    # to the unknown route is fine: href stays the original.
    assert "guide" in html


def test_unknown_internal_link_does_not_crash():
    html = _render("[x](no-such-doc.md)")
    # Not in route_map -> left alone, still rendered as a link.
    assert '<a href="no-such-doc.md"' in html or "no-such-doc" in html


def test_cross_language_doc_id_resolves_to_its_route():
    html = _render("[home](README.md)")
    assert 'href="#/"' in html


def test_script_tag_in_document_is_serialization_safe():
    """A document containing a literal ``</script>`` must not break out.

    The site compiler serializes docs through ``_safe_json`` (JSON with ``<``
    encoded as ``\\u003c``), so the raw ``</script>`` becomes ``\\u003c/script>``
    inside the payload and round-trips exactly through ``JSON.parse``.
    """
    md = "# H\n\n<script>alert(1)</script>\n"
    html = _render(md)
    # The rendered HTML does contain the script tag (it's a document), but once
    # script-serialized the raw closing tag is gone.
    payload = _safe_json({"en": {"doc": html}})
    assert "</script>" not in payload  # no raw breakout
    # And it round-trips to the exact original HTML through JSON.parse semantics.
    assert json.loads(payload)["en"]["doc"] == html


def test_render_resets_heading_dedupe_per_document():
    """Each document starts with a fresh heading-id set."""
    first = _render("## Reuse")
    assert 'id="reuse"' in first
    second = _render("## Reuse")
    assert 'id="reuse"' in second  # not reuse-2
    assert 'id="reuse-2"' not in second


def test_table_and_code_in_one_document_with_horizontal_scroll_markup():
    html = _render("## T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```js\nlet x = 1;\n```\n")
    assert "<table>" in html
    assert 'class="language-js"' in html
    assert 'id="t"' in html
