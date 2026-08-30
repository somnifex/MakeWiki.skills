"""Neutral stable-section parsing for multilingual section identity.

Multilingual documents are aligned by STABLE identity, never by localized
heading text or by heading position. The stable identity is the
``<!-- makewiki:section=<id> -->`` marker that precedes each reviewable section.
This module is the single source of truth for the section grammar and for the
validation that keeps section identity sound across the whole pipeline:

* ``parity`` and ``semantic-review`` pair sections by ``section_id``;
* the L4 verifier emits L4a FAILED checks for duplicate section IDs, orphan
  markers, and (in multilingual mode) a reviewable H2 with no marker;
* the L4b review-item registry derives ``L4b:<document_id>:<section_id>`` from
  these same section IDs.

Python only parses and validates structure here — it never judges whether two
localized sections carry the same meaning. The ``heading`` is display metadata
only and is never used as identity.
"""

from __future__ import annotations

import re
from typing import TypedDict

from pydantic import BaseModel, Field

# Stable section-ID grammar. Kept in sync with the marker every consumer
# recognizes: a slug of ASCII letters, digits, ``_``, ``.`` and ``-``.
SECTION_ID_PATTERN = re.compile(r"[A-Za-z0-9_.\-]+")

# A ``<!-- makewiki:section=<id> -->`` marker. The captured id is the identity.
_SECTION_MARKER = re.compile(
    r"<!--\s*makewiki:section=([A-Za-z0-9_.\-]+)\s*-->"
)

# Any heading line (H1..H6). A marker is satisfied when immediately followed by
# a heading of ANY level — the level under a section marker is display metadata
# (existing docs put H1/H2 under markers interchangeably) — but only H2 is
# treated as a REVIEWABLE heading for the missing-marker rule below.
_HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$")

# An H2 heading — a "reviewable" section heading. In multilingual mode every H2
# with no preceding marker is reported, because without a stable ID Python can
# only guess alignment.
_H2_PATTERN = re.compile(r"^##\s+(.+)$")

#: Marker line used when *writing* a stable section header. ``slug`` must
#: already match :data:`SECTION_ID_PATTERN`.
MARKER_PREFIX = "<!-- makewiki:section="
MARKER_SUFFIX = " -->"


def render_section_marker(slug: str) -> str:
    """Render the stable section marker for ``slug``.

    Returns ``<!-- makewiki:section=<slug> -->`` exactly. ``slug`` is emitted
    verbatim; callers are responsible for passing a slug matching
    :data:`SECTION_ID_PATTERN` (this mirrors the historical helper and keeps the
    written marker and parsed marker identical).
    """
    return f"{MARKER_PREFIX}{slug}{MARKER_SUFFIX}"


def is_valid_section_id(slug: str) -> bool:
    """Whether ``slug`` matches the section-ID grammar."""
    return bool(SECTION_ID_PATTERN.fullmatch(slug))


def section_ids(content: str) -> list[str]:
    """Return the ordered list of stable section IDs declared in ``content``."""
    return _SECTION_MARKER.findall(content)


class SectionRef(BaseModel):
    """One stable section of a document.

    ``section_id`` is the identity — shared across all language versions.
    ``heading`` is the *localized* H2 text; it is DISPLAY metadata only and must
    never be used as identity (languages may translate or reword it freely).
    ``content`` is the section body after the heading, up to the next marker
    (code fences and marker lines left intact for callers to strip). ``order``
    is the 0-based position within the document, also display-only — sections
    may be reordered across languages and still align by ``section_id``.
    """

    section_id: str
    heading: str = ""
    content: str = ""
    order: int = 0


class DocumentSections(BaseModel):
    """Parsed, validated stable-section view of one document.

    ``sections`` are in document order. Structural problems are reported as
    data (never raised) so a caller — normally the L4 verifier — can turn each
    into an L4a FAILED check:

    * ``duplicate_ids`` — a section ID declared more than once in this document.
    * ``orphan_markers`` — a marker NOT immediately followed by an H2 heading.
    * ``missing_marker_headings`` — an H2 heading with no preceding marker, only
      populated when ``require_markers`` is set (multilingual mode).
    """

    document_id: str = ""
    sections: list[SectionRef] = Field(default_factory=list)
    duplicate_ids: list[str] = Field(default_factory=list)
    orphan_markers: list[str] = Field(default_factory=list)
    missing_marker_headings: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether the document is structurally sound (no duplicate/orphan/id-absence)."""
        return not (self.duplicate_ids or self.orphan_markers or self.missing_marker_headings)


class _SectionState(TypedDict):
    """One section under construction; all keys str/list, in sync with parse."""

    id: str
    heading: str
    body: list[str]
    content: str


def parse_document_sections(
    content: str,
    *,
    document_id: str = "",
    require_markers: bool = False,
) -> DocumentSections:
    """Parse ``content`` into validated stable sections.

    Parameters
    ----------
    content:
        A single document's markdown. For the AUTHORITATIVE multilingual path
        callers pass ONE document (one language version) at a time; the section
        IDs then align across the per-language results.
    document_id:
        Stable document identity (e.g. ``base_name``) attached to the result.
    require_markers:
        When True (multilingual mode), a reviewable H2 heading with no preceding
        ``<!-- makewiki:section=<id> -->`` marker is reported in
        ``missing_marker_headings``. Without a stable ID, Python could only
        guess alignment by heading text or position — which is forbidden — so
        the absence is surfaced for the L4 layer to flag.

    The result is non-raising: structural problems (empty heading after a
    marker, orphan markers, duplicate IDs, marker-less H2s) are reported as
    fields on :class:`DocumentSections`, never thrown.
    """
    doc = DocumentSections(document_id=document_id)
    lines = content.splitlines()
    i = 0
    n = len(lines)
    sections: list[SectionRef] = []
    pending_marker_id: str | None = None
    order = 0

    # The section currently being built (after its heading). None until we hit
    # a heading that closes the previous section.
    current: _SectionState | None = None

    def flush_current() -> None:
        nonlocal current, order
        if current is None:
            return
        current["content"] = "\n".join(current["body"]).strip()
        sections.append(
            SectionRef(
                section_id=current["id"],
                heading=current["heading"],
                content=current["content"],
                order=order,
            )
        )
        order += 1
        current = None

    while i < n:
        line = lines[i].rstrip()
        marker = _SECTION_MARKER.search(line)
        if marker:
            flush_current()
            pending_marker_id = marker.group(1)
            i += 1
            continue

        heading_match = _HEADING_PATTERN.match(line)
        if heading_match:
            is_h2 = bool(_H2_PATTERN.match(line))
            # A heading may open a section if a marker precedes it, or close an
            # already-open one (marker-less heading inside a section).
            if pending_marker_id is not None:
                # Marker -> must be immediately followed by this heading.
                flush_current()
                sid = pending_marker_id
                pending_marker_id = None
                current = {
                    "id": sid,
                    "heading": heading_match.group(1).strip(),
                    "body": [],
                    "content": "",
                }
            else:
                # No marker before this heading: either an orphan from a marker
                # that was never followed by a heading, or a marker-less heading.
                if current is not None:
                    # Marker-less heading closes the open section.
                    flush_current()
                # Only an H2 is a REVIEWABLE section heading: in multilingual mode
                # it MUST carry a stable section marker, so report its absence.
                if require_markers and is_h2:
                    doc.missing_marker_headings.append(heading_match.group(1).strip())
                # Without a marker we do NOT open a stable section (no identity);
                # a non-H2 header (e.g. an H1 page title) is never reviewable.
            i += 1
            continue

        # Plain (non-H2, non-marker) line.
        if pending_marker_id is not None:
            # A marker was not followed by an H2 -> orphan marker.
            flush_current()
            doc.orphan_markers.append(pending_marker_id)
            # Treat the orphan marker's trailing block as an unmarked preamble
            # (no stable identity), so it cannot hold the document pending.
            pending_marker_id = None
            current = None
        elif current is not None:
            current["body"].append(line)
        i += 1

    if pending_marker_id is not None:
        # A trailing marker with nothing (no H2) after it.
        doc.orphan_markers.append(pending_marker_id)
        pending_marker_id = None
    flush_current()

    # ---- duplicates ---------------------------------------------------------
    seen: dict[str, int] = {}
    for sec in sections:
        seen[sec.section_id] = seen.get(sec.section_id, 0) + 1
    doc.duplicate_ids = [sid for sid, count in seen.items() if count > 1]
    doc.sections = sections
    return doc
