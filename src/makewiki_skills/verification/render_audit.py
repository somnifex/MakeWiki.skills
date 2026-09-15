"""Rendered-output audit (``verify-html``) — the mechanical net after rendering.

Renders can regress: leftover build markers, escaped content, dropped table
cells, unrendered fences. This module audits the GENERATED artifacts against
the Markdown that produced them, segment by segment:

* the compiled site is a single ``index.html`` SPA whose ``docsContent`` JSON
  embeds every (lang, document) rendered body, so the audit recovers the real
  artifact (never a re-render) and walks it per language and document;
* each document is split into the same H2-bounded segments on both sides —
  source segments (fence-aware, carrying ``<!-- makewiki:section=<id> -->``
  identity when authored) pair with rendered ``<h2>`` segments in order;
* each pair is checked item by item: marker residue, heading parity, prose
  coverage, code-block / table / callout parity, link/fence residue.

Export artifacts go through the same engine: printable HTML chapter by
chapter, EPUB chapter by chapter out of the archive.

Like ``lint-drafts`` this check fails closed: a missing artifact its target
covers is a blocking finding, and any critical/major finding fails the command
(exit 1) so the skill cannot ship a defective artifact. Minor findings are
recorded but never block. The Quality Gate's four-state semantics are
untouched — this is a post-render mechanical audit, not a new L0-L5 layer,
and it never judges prose quality.
"""

from __future__ import annotations

import html as _html
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field

from makewiki_skills.renderer.exporter import (
    collect_ordered_chapters,
    parse_export_chapters,
)
from makewiki_skills.renderer.site_compiler import (
    extract_docs_content,
    iter_plan_documents,
)
from makewiki_skills.review.section_parser import SECTION_MARKER_LINE, section_ids

__all__ = [
    "RenderFinding",
    "RenderAuditResult",
    "run_render_audit",
    "audit_markdown_pair",
]

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n?", re.DOTALL)
_H1_LINE_RE = re.compile(r"^#\s+(.+)$")
_H2_LINE_RE = re.compile(r"^##\s+(.+)$")
_BLOCK_MARKER_LINE_RE = re.compile(
    r"^\s*(?:\[\[id:[A-Za-z0-9_.\-]+\]\]|\[\[parity:ignore[^\]]*\]\])\s*$"
)
_FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_TABLE_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|(\s*:?-+:?\s*\|)+\s*$")
_IMAGE_TOKEN_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_CALLOUT_TOKEN_RE = re.compile(r"\[!(?:NOTE|TIP|WARNING|DANGER)\]", re.IGNORECASE)
_LIST_MARK_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

_MARKDOWN_MARKER_RESIDUE_RE = re.compile(r"\[\[id:|\[\[parity:")
_SECTION_MARKER_RESIDUE_RE = re.compile(
    r"<!--\s*makewiki:section=|&lt;!--\s*makewiki:section="
)
_ARTIFACT_PATH_RESIDUE_RE = re.compile(
    r"\.makewiki-artifacts/|12-drafts/|14-revision-results/"
)
_VISIBLE_CALLOUT_RESIDUE_RE = re.compile(r"\[!(?:NOTE|TIP|WARNING|DANGER)\]", re.IGNORECASE)
_FRONTMATTER_ECHO_RE = re.compile(
    r"^\s*(page_id|audience|page_type|source_claims):", re.MULTILINE
)
_LINK_RESIDUE_RE = re.compile(r"\]\(")
_FENCE_RESIDUE_RE = re.compile(r"```|~~~")
_CALL_STYLE_RE = re.compile(r'<blockquote class="callout\b')
_PRE_TAG_RE = re.compile(r"<pre\b")
_TABLE_TAG_RE = re.compile(r"<table\b")
_TR_TAG_RE = re.compile(r"<tr\b")
_TD_TAG_RE = re.compile(r"<t[dh]\b")
_H2_TAG_RE = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.DOTALL)

# Export bundle naming: documentation[.<lang>].html / .epub; EPUB chapters are
# chapter_NN_<slug>.xhtml inside the archive.
_EXPORT_HTML_RE = re.compile(r"documentation(?:\.(?P<lang>[A-Za-z0-9\-_]+))?\.html\Z")
_EXPORT_EPUB_RE = re.compile(r"documentation(?:\.(?P<lang>[A-Za-z0-9\-_]+))?\.epub\Z")
_EPUB_CHAPTER_RE = re.compile(r"chapter_\d+_(?P<slug>.+)\.xhtml\Z")
_CHAPTER_BODY_RE = re.compile(r"<body\b[^>]*>(.*)</body>", re.DOTALL)

#: A normalized prose line shorter than this is skipped: hr lines, short
#: labels and other syntax-only stretches would otherwise be false positives.
_MIN_PROSE_CHARS = 6

_SEVERITY = {
    "artifact_missing": "critical",
    "marker_leak": "critical",
    "heading_parity": "major",
    "prose_coverage": "major",
    "code_block_parity": "major",
    "table_integrity": "major",
    "link_residue": "major",
    "callout_fidelity": "minor",
}


def _fence_closes(line: str, fence: str) -> bool:
    """Whether ``line`` closes a fence opened with ``fence``` (``` or ~~~)."""
    return re.fullmatch(rf"\s{{0,3}}{re.escape(fence[0])}{{3,}}\s*", line) is not None


# ---------------------------------------------------------------------------
# data models
# ---------------------------------------------------------------------------


class RenderFinding(BaseModel):
    """One mechanical finding about a generated artifact, keyed to the source
    segment that produced it (ids follow the L4b review-item grammar)."""

    check: str  # marker_leak | heading_parity | prose_coverage | ...
    severity: str  # critical | major | minor
    language: str = ""
    document_id: str = ""
    section_id: str = ""
    message: str = ""
    source_excerpt: str = ""
    rendered_excerpt: str = ""


class RenderAuditResult(BaseModel):
    """Aggregated verify-html result. ``verdict`` is ``failed`` when any
    critical/major finding exists; minor findings never block delivery."""

    verdict: str  # "passed" | "failed"
    findings: list[RenderFinding] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    documents_audited: int = 0
    segments_audited: int = 0

    @property
    def blocking(self) -> list["RenderFinding"]:
        return [f for f in self.findings if f.severity in ("critical", "major")]


# ---------------------------------------------------------------------------
# shared normalization
# ---------------------------------------------------------------------------


def _alphanumeric_key(text: str) -> str:
    """Case-folded alphanumeric-only key: markdown formatting tokens, inline
    markup boundaries and HTML entities vanish identically on both sides of a
    containment comparison while real content loss still shows up."""
    return "".join(ch for ch in text if ch.isalnum()).casefold()


def _strip_tags(fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment))


class _SegmentTextCollector(HTMLParser):
    """Collect visible text of one rendered segment.

    ``all_text`` includes ``<pre>`` content; ``prose_text`` excludes it, so
    link/fence residue checks never fire on legitimate code content.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.all_parts: list[str] = []
        self.prose_parts: list[str] = []
        self.tag_counts: dict[str, int] = {}
        self._pre_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ARG002
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1
        if tag == "pre":
            self._pre_depth += 1

    def handle_startendtag(self, tag: str, attrs) -> None:  # noqa: ARG002
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre" and self._pre_depth:
            self._pre_depth -= 1

    def handle_data(self, data: str) -> None:
        self.all_parts.append(data)
        if not self._pre_depth:
            self.prose_parts.append(data)


def _segment_texts(html_fragment: str) -> tuple[str, str]:
    """Return ``(all visible text, visible text outside <pre>)``."""
    collector = _SegmentTextCollector()
    collector.feed(html_fragment)
    collector.close()
    return "".join(collector.all_parts), "".join(collector.prose_parts)


# ---------------------------------------------------------------------------
# segmentation (both sides split by the same H2 boundaries)
# ---------------------------------------------------------------------------


def segment_source_document(md: str) -> list[dict[str, str]]:
    """Split one Markdown document into ``[preamble, section, ...]`` segments.

    Sections are bounded by H2 headings — the same boundary the renderer
    emits — so both sides pair by position within one language version. A
    whole-line ``<!-- makewiki:section=<id> -->`` marker attaches its stable
    identity to the next section. The preamble (``heading == ""``) holds the
    stretch before the first H2.
    """
    segments: list[dict[str, str]] = []
    sid, heading, lines = "", "", []
    pending_marker: str | None = None
    fence: str | None = None

    for raw in md.splitlines():
        line = raw.rstrip()
        if fence is not None:
            if _fence_closes(line, fence):
                fence = None
            lines.append(line)
            continue
        open_match = _FENCE_OPEN_RE.match(line)
        if open_match:
            fence = open_match.group(1)
            lines.append(line)
            continue
        marker = SECTION_MARKER_LINE.match(line)
        if marker:
            pending_marker = marker.group(1)
            continue
        if _BLOCK_MARKER_LINE_RE.match(line):
            continue  # build metadata, not content
        h2 = _H2_LINE_RE.match(line)
        if h2:
            segments.append(
                {"section_id": sid, "heading": heading, "body": "\n".join(lines)}
            )
            sid, heading, lines = pending_marker or "", h2.group(1).strip(), []
            pending_marker = None
            continue
        lines.append(line)
    segments.append({"section_id": sid, "heading": heading, "body": "\n".join(lines)})

    # Stable identity attaches positionally when marker count matches section
    # count; a mismatch surfaces as a heading-parity finding instead of a
    # silently wrong pairing (cross-language identity stays with L4/L4b).
    markers = section_ids(md)
    sections = segments[1:]
    if len(markers) == len(sections):
        for seg, marker_id in zip(sections, markers):
            seg["section_id"] = marker_id
    return segments


def segment_rendered_document(body_html: str) -> list[dict[str, str]]:
    """Split rendered document HTML into ``[preamble, h2-section, ...]``.

    Mirrors :func:`segment_source_document`: the preamble is the stretch
    before the first ``<h2>``, then one segment per ``<h2>`` in document
    order.
    """
    parts = re.split(r"(?=<h2[\s>])", body_html)
    segments: list[dict[str, str]] = []
    for i, part in enumerate(parts):
        heading = ""
        if i > 0:
            h2 = _H2_TAG_RE.match(part)
            if h2:
                heading = _strip_tags(h2.group(1)).strip()
        segments.append({"heading": heading, "body": part})
    return segments


def _source_body_facts(body: str) -> dict:
    """Mechanical facts of one source segment: fence pairs, table structure,
    callout count, and the prose lines the coverage check compares."""
    fence: str | None = None
    fence_opens = 0
    table_rows = 0
    table_cells = 0
    callouts = 0
    prose: list[str] = []

    for raw in body.splitlines():
        line = raw.rstrip()
        if fence is not None:
            if _fence_closes(line, fence):
                fence = None
            continue  # fenced content is checked by count, never line-wise
        open_match = _FENCE_OPEN_RE.match(line)
        if open_match:
            fence = open_match.group(1)
            fence_opens += 1
            continue
        if _TABLE_LINE_RE.match(line):
            if _TABLE_SEP_RE.match(line):
                continue
            table_rows += 1
            table_cells += len(line.strip().strip("|").split("|"))
            continue
        callouts += len(_CALLOUT_TOKEN_RE.findall(line))
        if _BLOCK_MARKER_LINE_RE.match(line) or SECTION_MARKER_LINE.match(line):
            continue  # build metadata, not content
        prose.append(line)

    return {
        "prose": prose,
        "fence_pairs": fence_opens,
        "table_rows": table_rows,
        "table_cells": table_cells,
        "callouts": callouts,
    }


def _prose_key(md_line: str) -> str:
    """Normalization key of one source prose line: images drop (an ``<img>``
    renders no text), links keep only their label, callout tokens and list
    markers are rendered away, and all punctuation/whitespace is dropped so
    inline formatting can never mask real content loss."""
    s = _IMAGE_TOKEN_RE.sub(" ", md_line)
    s = _CALLOUT_TOKEN_RE.sub(" ", s)
    s = _MD_LINK_RE.sub(r"\1", s)
    s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)
    return _alphanumeric_key(s)


# ---------------------------------------------------------------------------
# per-segment checks
# ---------------------------------------------------------------------------


def _add_finding(
    findings: list[RenderFinding],
    *,
    check: str,
    language: str,
    document_id: str,
    section_id: str,
    message: str,
    source_excerpt: str = "",
    rendered_excerpt: str = "",
) -> None:
    findings.append(
        RenderFinding(
            check=check,
            severity=_SEVERITY[check],
            language=language,
            document_id=document_id,
            section_id=section_id,
            message=message,
            source_excerpt=source_excerpt[:200],
            rendered_excerpt=rendered_excerpt[:200],
        )
    )


def _check_marker_leak(
    findings: list[RenderFinding],
    *,
    language: str,
    document_id: str,
    section_id: str,
    seg_html: str,
    prose_text: str,
) -> None:
    """marker_leak — build metadata and internal orchestration residue must
    never reach a reader; every pattern here is a proven defect class."""
    for pattern, detail in (
        (
            _MARKDOWN_MARKER_RESIDUE_RE,
            "build marker residue ([[id:...]] / [[parity:ignore ...]]) visible in the artifact",
        ),
        (
            _SECTION_MARKER_RESIDUE_RE,
            "section marker residue (raw or escaped) in the rendered HTML",
        ),
        (
            _ARTIFACT_PATH_RESIDUE_RE,
            "internal artifact path leaked into the rendered output",
        ),
    ):
        hit = pattern.search(seg_html)
        if hit:
            findings.append(
                RenderFinding(
                    check="marker_leak",
                    severity="critical",
                    language=language,
                    document_id=document_id,
                    section_id=section_id,
                    message=f"{detail}: {hit.group(0)!r}",
                    rendered_excerpt=seg_html[max(0, hit.start() - 40) : hit.end() + 40],
                )
            )
            return
    visible = _VISIBLE_CALLOUT_RESIDUE_RE.search(prose_text)
    if visible:
        findings.append(
            RenderFinding(
                check="marker_leak",
                severity="critical",
                language=language,
                document_id=document_id,
                section_id=section_id,
                message=f"visible callout marker residue {visible.group(0)!r} outside a rendered callout",
                rendered_excerpt=prose_text[max(0, visible.start() - 40) : visible.end() + 40],
            )
        )


def _check_segment_pair(
    findings: list[RenderFinding],
    *,
    language: str,
    document_id: str,
    source: dict,
    rendered: dict,
    index: int,
) -> None:
    """Run every mechanical check over one (source, rendered) segment pair."""
    sid = str(source["section_id"])
    loc = sid or (str(source["heading"])[:40] if source["heading"] else f"segment-{index}")
    seg_html = rendered["body"]
    all_text, prose_text = _segment_texts(seg_html)
    target_key = _alphanumeric_key(all_text)
    src = _source_body_facts(str(source["body"]))

    # 1. marker_leak (critical).
    _check_marker_leak(
        findings,
        language=language,
        document_id=document_id,
        section_id=sid,
        seg_html=seg_html,
        prose_text=prose_text,
    )

    # 2. fence_residue — unrendered fences outside code blocks.
    residue = _FENCE_RESIDUE_RE.search(prose_text)
    if residue:
        _add_finding(
            findings,
            check="fence_residue",
            language=language,
            document_id=document_id,
            section_id=sid,
            message="unrendered code-fence marker visible in the rendered text",
            rendered_excerpt=prose_text[max(0, residue.start() - 40) : residue.end() + 40],
        )

    # 3. heading_parity — the section heading must survive rendering.
    if src_heading := str(source["heading"]):
        want = _alphanumeric_key(src_heading)
        got = _alphanumeric_key(rendered.get("heading", ""))
        if want != got:
            findings.append(
                RenderFinding(
                    check="heading_parity",
                    severity="major",
                    language=language,
                    document_id=document_id,
                    section_id=sid,
                    message=(
                        f"segment heading mismatch: source {src_heading!r} vs rendered "
                        f"{rendered.get('heading', '')!r} (positional pair #{index})"
                    ),
                    source_excerpt=src_heading,
                    rendered_excerpt=rendered.get("heading", ""),
                )
            )

    # 4. prose_coverage — every substantive source prose line must survive.
    missing = [
        line
        for line in src["prose"]
        if len(key := _prose_key(line)) >= _MIN_PROSE_CHARS and key not in target_key
    ]
    if missing:
        findings.append(
            RenderFinding(
                check="prose_coverage",
                severity="major",
                language=language,
                document_id=document_id,
                section_id=sid,
                message=(
                    f"{len(missing)} source prose line(s) missing from the rendered "
                    f"segment; first missing: {missing[0].strip()[:100]}"
                ),
                source_excerpt=missing[0].strip()[:200],
                rendered_excerpt=all_text[:160],
            )
        )

    # 5. code_block_parity.
    got_pre = len(_PRE_TAG_RE.findall(seg_html))
    if src["fence_pairs"] != got_pre:
        findings.append(
            RenderFinding(
                check="code_block_parity",
                severity="major",
                language=language,
                document_id=document_id,
                section_id=sid,
                message=(
                    f"source segment has {src['fence_pairs']} fenced block(s) but the "
                    f"rendered segment has {got_pre} <pre> block(s)"
                ),
            )
        )

    # 6. table_integrity.
    got_table = len(_TABLE_TAG_RE.findall(seg_html))
    got_rows = len(_TR_TAG_RE.findall(seg_html))
    got_cells = len(_TD_TAG_RE.findall(seg_html))
    if (src["table_rows"], src["table_cells"]) != (got_rows, got_cells) or (
        src["table_rows"] and not got_table
    ):
        findings.append(
            RenderFinding(
                check="table_integrity",
                severity="major",
                language=language,
                document_id=document_id,
                section_id=sid,
                message=(
                    f"table structure mismatch: source {src['table_rows']} row(s) / "
                    f"{src['table_cells']} cell(s) vs rendered {got_rows} / {got_cells}"
                ),
            )
        )

    # 7. callout_fidelity (minor).
    got_callouts = len(_CALL_STYLE_RE.findall(seg_html))
    if src["callouts"] != got_callouts:
        findings.append(
            RenderFinding(
                check="callout_fidelity",
                severity="minor",
                language=language,
                document_id=document_id,
                section_id=sid,
                message=(
                    f"source has {src['callouts']} callout(s) but the rendered segment "
                    f"has {got_callouts}"
                ),
            )
        )

    # 8. link_residue.
    residue = _LINK_RESIDUE_RE.search(prose_text)
    if residue:
        findings.append(
            RenderFinding(
                check="link_residue",
                severity="major",
                language=language,
                document_id=document_id,
                section_id=sid,
                message="unrendered markdown link syntax visible in the rendered text",
                rendered_excerpt=prose_text[max(0, residue.start() - 40) : residue.end() + 40],
            )
        )


# ---------------------------------------------------------------------------
# document driver: pair segments positionally, then check each pair
# ---------------------------------------------------------------------------


def audit_markdown_pair(
    *,
    language: str,
    document_id: str,
    source_md: str,
    rendered_html: str,
) -> tuple[list[RenderFinding], int]:
    """Audit one rendered document against its source Markdown.

    Both sides are segmented by the same H2 boundaries and paired by position
    (render order always equals source order within one language version);
    segment-count drift is itself a blocking finding. Returns
    ``(findings, segments_audited)``.
    """
    findings: list[RenderFinding] = []
    source_segments = segment_source_document(source_md)
    rendered_segments = segment_rendered_document(rendered_html)

    if len(source_segments) != len(rendered_segments):
        findings.append(
            RenderFinding(
                check="heading_parity",
                severity="major",
                language=language,
                document_id=document_id,
                message=(
                    f"segment count mismatch: source has {len(source_segments)} "
                    f"segment(s) (preamble + H2) but the rendered document has "
                    f"{len(rendered_segments)}"
                ),
            )
        )

    for index, (src, got) in enumerate(zip(source_segments, rendered_segments)):
        _check_segment_pair(
            findings,
            language=language,
            document_id=document_id,
            source=src,
            rendered=got,
            index=index,
        )

    # Document headline parity: the source H1 must exist as a rendered <h1>.
    h1_match = _H1_LINE_RE.search(str(source_segments[0]["body"]))
    if h1_match:
        want = _alphanumeric_key(h1_match.group(1))
        got_headings = [
            _alphanumeric_key(_strip_tags(inner))
            for inner in re.findall(r"<h1\b[^>]*>(.*?)</h1>", rendered_html, re.DOTALL)
        ]
        if want not in got_headings:
            findings.append(
                RenderFinding(
                    check="heading_parity",
                    severity="major",
                    language=language,
                    document_id=document_id,
                    message=f"document H1 {h1_match.group(1)!r} missing from the rendered headings",
                    source_excerpt=h1_match.group(1),
                )
            )

    return findings, len(source_segments)
     


# ---------------------------------------------------------------------------
# artifact drivers
# ---------------------------------------------------------------------------


def _load_site_plan(makewiki_dir: Path):
    """Load the LLM-authored SitePresentationPlan, or ``None`` when absent."""
    from makewiki_skills.model.site_presentation import load_site_presentation

    for name in ("site_presentation.json", "site_presentation.yaml", "site_presentation.yml"):
        probe = makewiki_dir / name
        if probe.is_file():
            try:
                return load_site_presentation(probe)
            except Exception:  # noqa: BLE001 - invalid plan: report as missing
                return None
    return None


def _resolve_default_language(makewiki_dir: Path) -> str:
    """Resolve the default language with the same priority the CLI uses:
    SitePresentationPlan.default_language > makewiki.config.yaml > ``en``."""
    plan = _load_site_plan(makewiki_dir)
    if plan is not None:
        return plan.default_language
    for probe in (makewiki_dir / "makewiki.config.yaml", makewiki_dir.parent / "makewiki.config.yaml"):
        if probe.is_file():
            try:
                from makewiki_skills.config import MakeWikiConfig

                return MakeWikiConfig.load(probe, makewiki_dir).default_language
            except Exception:  # noqa: BLE001 - corrupt config: next authority
                break
    return "en"


def _audit_site_artifact(
    makewiki_dir: Path,
    *,
    langs: list[str] | None,
    plan,
) -> tuple[list[str], list[RenderFinding], int, int]:
    """Audit ``site/index.html`` against the plan's Markdown sources."""
    artifacts: list[str] = []
    findings: list[RenderFinding] = []
    documents = segments = 0

    index_path = makewiki_dir / "site" / "index.html"
    if not index_path.is_file():
        findings.append(
            RenderFinding(
                check="artifact_missing",
                severity="critical",
                message=(
                    f"site/index.html not found under {makewiki_dir}; run build-site "
                    "before verify-html --target site"
                ),
            )
        )
        return artifacts, findings, documents, segments

    artifacts.append(str(index_path))
    if plan is None:
        findings.append(
            RenderFinding(
                check="artifact_missing",
                severity="critical",
                language="",
                document_id="site",
                message=(
                    "no SitePresentationPlan found next to the wiki directory; "
                    "the site audit cannot resolve which documents shipped"
                ),
            )
        )
        return artifacts, findings, documents, segments

    try:
        with Path(makewiki_dir, "site", "index.html").open(encoding="utf-8", errors="replace") as fh:
            shipped = extract_docs_content(fh.read())
    except (OSError, ValueError) as exc:
        findings.append(
            RenderFinding(
                check="artifact_missing",
                severity="critical",
                message=f"site/index.html unreadable or not a compiled MakeWiki site: {exc}",
            )
        )
        return artifacts, findings, documents, segments

    wanted = {lang for lang in langs} if langs else None
    for lang, doc_id, source_md in iter_plan_documents(makewiki_dir, plan):
        if wanted is not None and lang not in wanted:
            continue
        body = shipped.get(lang, {}).get(doc_id)
        if body is None:
            # Mechanical absence: a missing translation falls back across
            # languages in the SPA and is the plan's concern, not a format
            # defect in what was shipped.
            continue
        pair_findings, pair_segments = audit_markdown_pair(
            language=lang,
            document_id=doc_id,
            source_md=source_md,
            rendered_html=body,
        )
        findings.extend(pair_findings)
        segments += pair_segments
        documents += 1
    return artifacts, findings, documents, segments


def _audit_export_bundle(
    makewiki_dir: Path,
    bundle: Path,
    *,
    default_language: str,
    langs: list[str] | None,
    findings: list[RenderFinding],
) -> tuple[int, int]:
    """Audit one printable-HTML or EPUB export bundle chapter by chapter."""
    from makewiki_skills.renderer.exporter import collect_ordered_chapters, parse_export_chapters

    html_match = _EXPORT_HTML_RE.fullmatch(bundle.name)
    epub_match = None if html_match else _EXPORT_EPUB_RE.fullmatch(bundle.name)
    if html_match:
        language = html_match.group("lang") or default_language
        chapters = parse_export_chapters(bundle.read_text(encoding="utf-8", errors="replace"))
    elif epub_match:
        language = epub_match.group("lang") or default_language
        chapters = []
        with zipfile.ZipFile(bundle) as archive:
            for name in sorted(n for n in archive.namelist() if _EPUB_CHAPTER_RE.search(n)):
                slug_match = _EPUB_CHAPTER_RE.match(Path(name).name)
                body_match = _CHAPTER_BODY_RE.search(archive.read(name).decode("utf-8", "replace"))
                if slug_match and body_match:
                    chapters.append((slug_match.group("slug"), body_match.group(1)))
    else:
        return 0, 0  # not a MakeWiki export artifact; nothing to audit here

    if langs and language not in langs:
        return 0, 0

    source_by_slug = {
        slug: raw_md
        for _title, raw_md, slug in collect_ordered_chapters(
            makewiki_dir, language, default_language
        )
    }
    documents = segments = 0
    for chapter_slug, body in chapters:
        raw_md = source_by_slug.pop(chapter_slug, None)
        if raw_md is None:
            findings.append(
                RenderFinding(
                    check="artifact_completeness",
                    severity="major",
                    language=language,
                    document_id=chapter_slug,
                    message="exported chapter has no matching source Markdown chapter",
                )
            )
            continue
        pair_findings, pair_segments = audit_markdown_pair(
            language=language,
            document_id=chapter_slug,
            source_md=raw_md,
            rendered_html=body,
        )
        findings.extend(pair_findings)
        segments += pair_segments
        documents += 1
    for leftover in source_by_slug:
        findings.append(
            RenderFinding(
                check="artifact_completeness",
                severity="major",
                language=language,
                document_id=leftover,
                message="source chapter missing from the compiled export",
            )
        )
    return documents, segments


def _audit_export_artifacts(
    makewiki_dir: Path,
    *,
    default_language: str,
    langs: list[str] | None,
    require_bundles: bool,
) -> tuple[list[str], list[RenderFinding], int, int]:
    """Audit every export bundle under ``<dir>/export``.

    Fails closed: when ``require_bundles`` is set (explicit ``--target export``)
    and no bundle exists, that is a blocking finding — the flow asked to audit
    exports and none were delivered.
    """
    artifacts: list[str] = []
    findings: list[RenderFinding] = []
    documents = segments = 0
    export_dir = makewiki_dir / "export"
    bundles: list[Path] = []
    if export_dir.is_dir():
        bundles = sorted(export_dir.glob("documentation*.html")) + sorted(
            export_dir.glob("documentation*.epub")
        )
    if not bundles:
        if require_bundles:
            findings.append(
                RenderFinding(
                    check="artifact_missing",
                    severity="critical",
                    message=(
                        f"no export bundles found under {export_dir}; run export "
                        "before verify-html --target export"
                    ),
                )
            )
        return artifacts, findings, documents, segments
    for bundle_path in bundles:
        docs, segs = _audit_export_bundle(
            makewiki_dir,
            bundle_path,
            default_language=default_language,
            langs=langs,
            findings=findings,
        )
        artifacts.append(str(bundle_path))
        documents += docs
        segments += segs
    return artifacts, findings, documents, segments


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------


def run_render_audit(
    makewiki_dir: Path | str,
    *,
    target: str = "all",
    langs: list[str] | None = None,
    default_language: str | None = None,
) -> RenderAuditResult:
    """Audit generated artifacts for one makewiki directory.

    ``target``: ``site`` (site/index.html required), ``export`` (at least one
    export bundle required) or ``all`` (site required; exports audited when
    present). Verdict is ``failed`` when any critical/major finding exists.
    """
    if target not in ("site", "export", "all"):
        raise ValueError(f"unknown --target {target!r}; expected site | export | all")

    makewiki_dir = Path(makewiki_dir).resolve()
    resolved_default = default_language or _resolve_default_language(makewiki_dir)
    plan = _load_site_plan(makewiki_dir) if target in ("site", "all") else None

    artifacts: list[str] = []
    findings: list[RenderFinding] = []
    documents = segments = 0

    if target in ("site", "all"):
        art, fnd, docs, segs = _audit_site_artifact(makewiki_dir, langs=langs, plan=plan)
        artifacts.extend(art)
        findings.extend(fnd)
        documents += docs
        segments += segs

    if target in ("export", "all"):
        art, fnd, docs, segs = _audit_export_artifacts(
            makewiki_dir,
            default_language=resolved_default,
            langs=langs,
            require_bundles=(target == "export"),
        )
        artifacts.extend(art)
        findings.extend(fnd)
        documents += docs
        segments += segs

    verdict = "failed" if any(f.severity in ("critical", "major") for f in findings) else "passed"
    return RenderAuditResult(
        verdict=verdict,
        findings=findings,
        artifacts=artifacts,
        documents_audited=documents,
        segments_audited=segments,
    )
