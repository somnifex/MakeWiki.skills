"""L4 Cross-Language Verifier: mechanical code-block parity + semantic prose parity.

L4 is split into two sub-reports:

* **L4a (mechanical)** — Python can prove this deterministically:
  - fact-delta parity (commands / config keys present in one language but not
    another),
  - stable-block-ID SHA256 parity: code blocks tagged with ``[[id:...]]`` are
    matched across languages by their ID (never by position) and compared by a
    SHA256 of the normalized body. Identical bodies pass, diverged bodies fail,
    and a block missing from a language fails (the mechanical harmonizer could
    not prove it is the same logical block).
  - untagged-technical-block parity: every technical fenced block (bash/json/
    yaml/… without a ``[[id:...]]`` marker) is flagged so it cannot silently
    bypass parity. A technical block may be exempted ONLY by an explicit
    ``[[parity:ignore reason="..."]]`` marker.
  - Stable-identity structural invariants: a stable section ID declared more
    than once in one document, a duplicated stable block ID within one logical
    document, and (in multilingual output) a reviewable H2 with no stable
    section marker or an orphan marker — each is a mechanical FAILURE.
  Block/product identity is keyed on STABLE IDs — section markers
  (``<!-- makewiki:section=<slug> -->``) and ``[[id:...]]`` block IDs — never on
  heading text or heading position, because languages may legitimately reorder
  their sections. Block identity is namespaced by ``(document_id, section_id,
  block_id)`` so two different pages may both declare ``install.command``
  without colliding.
  L4a checks are emitted with ``claim_type="l4a_mechanical"`` and may be passed.

* **L4b (semantic)** — prose parity is *meaning*, which Python cannot judge. It
  always emits a single ``pending`` check reserved for the LLM Auditor, so the
  layer never reports a vacuous ``passed`` on semantics alone.
  L4b checks are emitted with ``claim_type="l4b_semantic"``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer
from makewiki_skills.review.section_parser import (
    parse_document_sections,
    render_section_marker,
    section_ids,
)
from makewiki_skills.verification.report import LayerReport, VerificationCheck

# Re-exported from section_parser.py (the single source of truth for the section
# grammar) so existing callers importing these helpers from this module keep
# working. ``split_sections`` below remains a thin wrapper over
# ``parse_document_sections``.
__all__ = [
    "BlockRef",
    "L4CrossLanguageVerifier",
    "extract_blocks_by_id",
    "pair_blocks_by_section_id",
    "render_section_marker",
    "section_ids",
    "split_sections",
    "stable_block_content_hash",
]

_BLOCK_ID_PATTERN = re.compile(r"\[\[id:([A-Za-z0-9_.\-]+)\]\]")
_PARITY_IGNORE_PATTERN = re.compile(r"\[\[parity:ignore(?:[^\]]*)\]\]")
# Marker pattern used by ``_scan_blocks`` to track the current section while
# walking block code. Mirrors section_parser's grammar (which is the authority);
# _scan_blocks may read markers directly because it only needs the id, not the
# parser's structural validation.
_SECTION_MARKER_PATTERN = re.compile(r"<!--\s*makewiki:section=([A-Za-z0-9_.\-]+)\s*-->")
_CODE_BLOCK_PATTERN = re.compile(
    r"```(?P<lang>[a-zA-Z0-9_\-\+]*)\n(?P<code>.*?)```", re.DOTALL
)

# Language tags that mark a fenced block as TECHNICAL (must carry a stable ID).
# Any fenced block whose tag is NOT in this set is treated as a non-technical
# (prose/illustrative) fence and is exempt from the untagged-block requirement.
TECHNICAL_LANGUAGES: frozenset[str] = frozenset(
    {
        "bash",
        "sh",
        "shell",
        "zsh",
        "console",
        "powershell",
        "ps1",
        "cmd",
        "batch",
        "json",
        "yaml",
        "yml",
        "toml",
        "ini",
        "xml",
        "hocon",
        "conf",
        "env",
        "python",
        "py",
        "js",
        "javascript",
        "ts",
        "typescript",
        "sql",
        "dockerfile",
        "makefile",
        "code",
        "java",
        "kotlin",
        "scala",
        "go",
        "golang",
        "c",
        "cpp",
        "csharp",
        "ruby",
        "php",
        "rust",
        "swift",
        "r",
        "perl",
        "lua",
        "graphql",
        "protobuf",
        "terraform",
        "hcl",
        "css",
        "scss",
        "html",
        "http",
        "regex",
        "text",
    }
)


@dataclass(frozen=True)
class BlockRef:
    """A single fenced code block located by stable identity, not position."""

    language: str
    section_id: str  # "" when the document declares no section markers
    block_id: str  # "" for an untagged block
    full_block: str
    content_hash: str
    is_technical: bool
    exempted: bool  # carries an explicit [[parity:ignore ...]] marker
    document_id: str = ""  # base_name of the document the block was found in

    @property
    def stable_key(self) -> tuple[str, str, str]:
        """(document_id, section_id, block_id) triple used to match a block."""
        return (self.document_id, self.section_id, self.block_id)


def stable_block_content_hash(code: str) -> str:
    """Stable SHA256-derived content hash of a code block body (16 hex chars).

    Mirrors the mechanical harmonizer's ``_content_hash`` so L4 parity and the
    revision engine agree on block identity.
    """
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def split_sections(doc: str) -> list[tuple[str, str]]:
    """Split ``doc`` into ``(section_id, content)`` chunks via the parser.

    Delegates to :func:`parse_document_sections` (the single source of truth for
    section grammar). Each chunk is ``(SectionRef.section_id,
    SectionRef.content)`` — the section body after the H2 heading. When ``doc``
    declares no section markers this returns ``[("", doc)]`` so callers can fall
    back to pairing by block ID alone.
    """
    sections = parse_document_sections(doc).sections
    if not sections:
        return [("", doc)]
    return [(sec.section_id, sec.content) for sec in sections]


def extract_blocks_by_id(content: str) -> dict[str, tuple[str, str]]:
    """Map each stable block ID to its ``(full_block_text, content_hash)``.

    The ID marker may precede the fence or be the first line inside the fence
    body — the same scheme the revision engine's harmonizer uses.
    """
    blocks: dict[str, tuple[str, str]] = {}
    for ref in _scan_blocks(content, "en"):
        if ref.block_id:
            blocks[ref.block_id] = (ref.full_block, ref.content_hash)
    return blocks


def pair_blocks_by_section_id(
    documents: dict[str, list[DocumentArtifact]],
) -> dict[tuple[str, str, str], dict[str, BlockRef]]:
    """Group fenced+tagged blocks by (document_id, section_id, block_id).

    **Stable public data contract** (consumed by the orchestrator / CLI / the
    cross-language reviewer):

    ``documents`` maps a language code to the list of rendered documents for
    that language; each artifact carries ``.base_name`` (the explicit document
    namespace) and ``.content``.

    Returns a deterministic mapping ``{(document_id, section_id, block_id):
    {language: BlockRef}}``. ``document_id`` is ALWAYS the document's
    ``base_name`` — never inferred from incidental filename grouping. A block is
    included only if it carries a stable ``[[id:...]]`` marker; the section key
    is the nearest preceding ``<!-- makewiki:section=<slug> -->`` marker
    (``""`` when the document spans no section markers). Matching is therefore
    keyed on stable identity (document + section + block ID), never on heading
    text or heading position — languages may reorder sections and the same block
    still pairs correctly. Blocks whose ``block_id == ""`` (untagged) are
    excluded: they are separately audited as untagged-technical failures.

    Two different pages may both declare ``install.command``; because the key is
    namespaced by ``document_id`` they never collide.

    The mapping is deterministic: languages, documents and blocks are visited in
    sorted order and every language present for a given key appears in the inner
    dict (at most one ``BlockRef`` per language per key).
    """
    paired: dict[tuple[str, str, str], dict[str, BlockRef]] = {}
    for lang in sorted(documents):
        for doc in documents[lang]:
            base = doc.base_name
            for ref in _scan_blocks(doc.content, lang):
                if not ref.block_id:
                    continue
                ref = replace(ref, document_id=base)
                key = (base, ref.section_id, ref.block_id)
                paired.setdefault(key, {})[lang] = ref
    return paired


def _block_id_in_body(full_block: str) -> str | None:
    """Return a block ID declared as the first line inside the fence body, if any."""
    first_inner_line = full_block.split("\n", 1)[1] if "\n" in full_block else ""
    match = _BLOCK_ID_PATTERN.search(first_inner_line)
    return match.group(1) if match else None


def _scan_blocks(content: str, language: str) -> list[BlockRef]:
    """Scan ``content`` and return every fenced code block as a ``BlockRef``.

    Tracks the current section ID from ``<!-- makewiki:section=<slug> -->``
    markers, a pending ``[[id:...]]`` and a pending ``[[parity:ignore ...]]``
    marker (each may precede the fence or be the first line inside the fence
    body). An untagged technical block still yields a ``BlockRef`` (``block_id``
    is ``""`` and ``exempted`` reflects any ``[[parity:ignore ...]]`` marker) so
    it can be audited rather than silently skipped.
    """
    blocks: list[BlockRef] = []
    lines = content.splitlines(keepends=True)
    section = ""
    pending_id: str | None = None
    pending_ignore = False
    i = 0
    while i < len(lines):
        line = lines[i]
        sec = _SECTION_MARKER_PATTERN.search(line)
        if sec:
            section = sec.group(1)
            i += 1
            continue
        id_match = _BLOCK_ID_PATTERN.search(line)
        if id_match:
            pending_id = id_match.group(1)
            i += 1
            continue
        if _PARITY_IGNORE_PATTERN.search(line):
            pending_ignore = True
            i += 1
            continue
        if line.lstrip().startswith("```"):
            marker_lines: list[str] = []
            if (i - 1) >= 0 and (
                _BLOCK_ID_PATTERN.search(lines[i - 1])
                or _PARITY_IGNORE_PATTERN.search(lines[i - 1])
            ):
                marker_lines.append(lines[i - 1])
            block_lines = marker_lines + [line]
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                block_lines.append(lines[j])
                j += 1
            if j < len(lines):
                block_lines.append(lines[j])
                j += 1
            full_block = "".join(block_lines)
            lang_match = re.match(r"```([a-zA-Z0-9_\-+]*)", line.lstrip())
            lang_tag = (lang_match.group(1).lower() if lang_match else "").strip()
            code_match = _CODE_BLOCK_PATTERN.search(full_block)
            code_body = code_match.group("code") if code_match else ""

            body_id = pending_id or _block_id_in_body(full_block)
            body_ignore = pending_ignore or bool(_PARITY_IGNORE_PATTERN.search(full_block))

            blocks.append(
                BlockRef(
                    language=language,
                    section_id=section,
                    block_id=body_id or "",
                    full_block=full_block,
                    content_hash=stable_block_content_hash(code_body),
                    is_technical=lang_tag in TECHNICAL_LANGUAGES,
                    exempted=body_ignore,
                )
            )
            i = j
            pending_id = None
            pending_ignore = False
            continue
        i += 1
    return blocks


class L4CrossLanguageVerifier:
    """Verify factual parity across all multilingual documentation versions."""

    def __init__(self) -> None:
        self._reviewer = CrossLanguageReviewer()

    def verify_documents(
        self,
        documents: dict[str, list[DocumentArtifact]],
    ) -> LayerReport:
        languages = list(documents.keys())
        checks: list[VerificationCheck] = []

        # ---- Stable-identity structural invariants (any language count) ------
        # A duplicate stable section ID or a duplicated stable block ID is a
        # per-document structural failure regardless of how many languages are
        # generated, so it is checked before the language-count branch.
        checks.extend(self._duplicate_section_id_checks(documents))
        checks.extend(self._duplicate_block_id_checks(documents))

        if len(languages) < 2:
            # With a single language there is nothing to compare for parity, so
            # cross-language verification is genuinely not applicable. It must
            # never be reported as "passed" - no parity check actually ran.
            checks.append(
                VerificationCheck(
                    layer="L4",
                    target="all",
                    language_code="all",
                    claim_type="l4a_mechanical",
                    claim_text="Single language generation",
                    verified=False,
                    status="not_applicable",
                    verification_source="not_executed",
                    detail="Single language generated; cross-language parity is not applicable",
                )
            )
            checks.append(
                VerificationCheck(
                    layer="L4",
                    target="all",
                    language_code="all",
                    claim_type="l4b_semantic",
                    claim_text="Semantic prose parity",
                    verified=False,
                    status="not_applicable",
                    verification_source="not_executed",
                    detail="Single language generated; semantic prose parity is not applicable",
                    review_item_id="L4b:all:not-applicable",
                )
            )
            return LayerReport(
                layer="L4",
                name="Cross-Language",
                checks=checks,
            )

        # ---- Multilingual stable-section invariants --------------------------
        # In multilingual output every reviewable H2 MUST carry a stable section
        # marker and every marker MUST be followed by an H2.
        checks.extend(self._missing_multilingual_section_id_checks(documents))

        # ---- L4a mechanical: fact deltas ------------------------------------
        review = self._reviewer.review(documents)
        for delta in review.fact_deltas:
            is_critical = delta.severity == "critical"
            checks.append(
                VerificationCheck(
                    layer="L4",
                    target=f"{delta.fact_type}:{delta.value}",
                    language_code=",".join(delta.missing_from),
                    claim_type="l4a_mechanical",
                    claim_text=f"{delta.fact_type} '{delta.value}' missing from {delta.missing_from}",
                    verified=not is_critical,
                    status="failed" if is_critical else "warning",
                    verification_source="cross_language_analyzer",
                    detail=f"Present in {delta.present_in} but missing from {delta.missing_from}",
                    suggested_fix=f"Add missing {delta.fact_type} to {', '.join(delta.missing_from)}",
                )
            )

        # ---- L4a mechanical: untagged technical block audit ------------------
        # A technical fence with no [[id:...]] would silently bypass parity by
        # position. Flag it so every technical block is provably accounted for.
        checks.extend(self._untagged_block_checks(documents, languages))

        # ---- L4a mechanical: stable-block-ID SHA256 parity -------------------
        checks.extend(self._stable_block_parity_checks(documents))

        # ---- L4b semantic: prose parity is reserved for the LLM Auditor ------
        checks.extend(self._l4b_semantic_section_checks(documents))

        return LayerReport(
            layer="L4",
            name="Cross-Language",
            checks=checks,
        )

    @staticmethod
    def _duplicate_section_id_checks(
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[VerificationCheck]:
        """Emit an L4a failure per duplicated stable section ID (§9).

        A section ID is identity shared across a document's language versions;
        declaring the same ID more than once in ONE document is a structural
        invariant violation, so it is checked for every document regardless of
        the number of generated languages.
        """
        checks: list[VerificationCheck] = []
        for lang, doc_list in sorted(documents.items()):
            for doc in doc_list:
                parsed = parse_document_sections(
                    doc.content, document_id=doc.base_name
                )
                for sid in parsed.duplicate_ids:
                    checks.append(
                        VerificationCheck(
                            layer="L4",
                            target=doc.base_name,
                            language_code=lang,
                            claim_type="l4a_mechanical",
                            claim_text=(
                                f"Stable section id '{sid}' declared more than once "
                                f"in {doc.base_name}"
                            ),
                            verified=False,
                            status="failed",
                            verification_source="cross_language_analyzer",
                            detail=(
                                f"Section id '{sid}' appears more than once in "
                                f"{doc.base_name}; a section ID must be unique per "
                                "document/language because it is the stable identity "
                                "sections are aligned on across languages"
                            ),
                            suggested_fix=(
                                "Rename one of the duplicate "
                                "`<!-- makewiki:section=... -->` markers"
                            ),
                        )
                    )
        return checks

    @staticmethod
    def _duplicate_block_id_checks(
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[VerificationCheck]:
        """Emit an L4a failure per duplicated stable block ID within one doc (§8).

        Unlike the ``extract_blocks_by_id`` dict — which silently overwrites on
        collision — this counts occurrences explicitly so a duplicated block ID
        is surfaced as a failure rather than masked. Applied per logical document
        (one document in one language); untagged blocks are excluded.
        """
        checks: list[VerificationCheck] = []
        for lang, doc_list in sorted(documents.items()):
            for doc in doc_list:
                counts: dict[str, int] = {}
                for ref in _scan_blocks(doc.content, lang):
                    if not ref.block_id:
                        continue
                    counts[ref.block_id] = counts.get(ref.block_id, 0) + 1
                for block_id, count in sorted(counts.items()):
                    if count <= 1:
                        continue
                    checks.append(
                        VerificationCheck(
                            layer="L4",
                            target=f"[[id:{block_id}]]",
                            language_code=lang,
                            claim_type="l4a_mechanical",
                            claim_text=(
                                f"Duplicate stable block id '{block_id}' in "
                                f"{doc.base_name}"
                            ),
                            verified=False,
                            status="failed",
                            verification_source="cross_language_analyzer",
                            detail=(
                                f"Stable block id '{block_id}' appears more than once "
                                f"in {doc.base_name}; duplicate block ids must be "
                                "unique within one logical document"
                            ),
                            suggested_fix=(
                                "Rename one of the duplicate [[id:...]] markers so "
                                "each block has a unique stable ID"
                            ),
                        )
                    )
        return checks

    @staticmethod
    def _multi_language_bases(
        documents: dict[str, list[DocumentArtifact]],
    ) -> set[str]:
        """Base names that genuinely span >=2 non-empty languages.

        A base document is only cross-language-reviewable when at least two
        languages actually carry it. Relying on ``len(documents)`` alone is wrong:
        a single-language wiki loaded with a default ``["en", "zh-CN"]`` language
        list still produces two language KEYS, but ``zh-CN`` is an empty list, so
        no page is genuinely multilingual. The missing-marker strictness (§4)
        must therefore be keyed per base on real multi-language presence — the
        same notion :meth:`_l4b_semantic_section_checks` uses for prose-parity
        reviewability — never on language-key count.
        """
        base_langs: dict[str, set[str]] = {}
        for lang, doc_list in documents.items():
            if not doc_list:
                continue  # a language key with no documents carries no page
            for doc in doc_list:
                base_langs.setdefault(doc.base_name, set()).add(lang)
        return {base for base, langs in base_langs.items() if len(langs) >= 2}

    @staticmethod
    def _missing_multilingual_section_id_checks(
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[VerificationCheck]:
        """Emit L4a failures for marker-less reviewable H2s and orphan markers.

        Only meaningful in multilingual output (§4/§5): every reviewable H2 in a
        genuinely multi-language document MUST carry a stable section marker, and
        every marker MUST be immediately followed by an H2. Emits one failure per
        marker-less H2 and one failure per document that carries an orphan marker.

        Strictness is gated per base document on it spanning >=2 non-empty
        languages (:meth:`_multi_language_bases`); a page that only exists in one
        language (or an empty language list) is single-language output for that
        page and markers are not required there.
        """
        checks: list[VerificationCheck] = []
        multi_bases = L4CrossLanguageVerifier._multi_language_bases(documents)
        for lang, doc_list in sorted(documents.items()):
            for doc in doc_list:
                if doc.base_name not in multi_bases:
                    continue  # not genuinely multilingual -> markerless H2s are fine
                parsed = parse_document_sections(
                    doc.content, document_id=doc.base_name, require_markers=True
                )
                for heading in parsed.missing_marker_headings:
                    checks.append(
                        VerificationCheck(
                            layer="L4",
                            target=doc.base_name,
                            language_code=lang,
                            claim_type="l4a_mechanical",
                            claim_text="Reviewable H2 without stable section marker",
                            verified=False,
                            status="failed",
                            verification_source="cross_language_analyzer",
                            detail=(
                                f"H2 heading '{heading}' in {doc.base_name} ({lang}) has "
                                "no preceding `<!-- makewiki:section=<id> -->` marker; "
                                "without a stable ID Python could only guess alignment "
                                "by heading text or position, which is forbidden. In "
                                "multilingual output every reviewable H2 MUST carry a "
                                "stable section ID."
                            ),
                            suggested_fix=(
                                "Add `<!-- makewiki:section=<slug> -->` immediately "
                                "before this H2 (or make the section non-reviewable)."
                            ),
                        )
                    )
                if parsed.orphan_markers:
                    checks.append(
                        VerificationCheck(
                            layer="L4",
                            target=doc.base_name,
                            language_code=lang,
                            claim_type="l4a_mechanical",
                            claim_text=(
                                f"Orphan section marker '{parsed.orphan_markers[0]}' "
                                f"in {doc.base_name} not followed by an H2 heading"
                            ),
                            verified=False,
                            status="failed",
                            verification_source="cross_language_analyzer",
                            detail=(
                                "An orphan marker is a "
                                "`<!-- makewiki:section=<id> -->` marker that is not "
                                "immediately followed by an H2 heading; a stable "
                                "section ID must label a reviewable section."
                            ),
                            suggested_fix=(
                                "Place the marker immediately before the H2 heading "
                                "it labels, or remove the stray marker"
                            ),
                        )
                    )
        return checks

    @staticmethod
    def _l4b_semantic_section_checks(
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[VerificationCheck]:
        """Emit per-section ``l4b_semantic`` pending checks for multi-language docs.

        Each base document present in >=2 languages contributes one pending l4b
        check PER stable section (derived from ``parse_document_sections`` so the
        section id is the true stable identity). Prose-parity passage is keyed by
        a stable ``review_item_id`` of form ``L4b:<base_name>:<section_id>``. A
        section with no stable marker id (``section_id == ""``) is skipped — there
        is no stable identity to review against.

        If no base document yields a per-section check (e.g. no section markers,
        or no document spans >=2 languages) a single synthetic pending l4b check
        is emitted so the multi-language L4 layer still carries at least one
        `claim_type == "l4b_semantic"` check (the Quality Gate depends on it).
        """
        # base_name -> {language_code: content}
        base_contents: dict[str, dict[str, str]] = {}
        for lang, doc_list in documents.items():
            for doc in doc_list:
                base_contents.setdefault(doc.base_name, {})[lang] = doc.content

        l4b_checks: list[VerificationCheck] = []
        for base_name in sorted(base_contents):
            lang_map = base_contents[base_name]
            if len(lang_map) < 2:
                continue  # single-language base doc: no prose-parity passage
            lang_codes = ",".join(sorted(lang_map))
            rep_lang = sorted(lang_map)[0]
            sections = parse_document_sections(
                lang_map[rep_lang], document_id=base_name
            ).sections
            seen: set[str] = set()
            for sec in sections:
                sid = sec.section_id
                if not sid:
                    continue  # no stable identity to review against
                if sid in seen:
                    sid = f"{sid}-{sec.order}"
                seen.add(sid)
                l4b_checks.append(
                    VerificationCheck(
                        layer="L4",
                        target=base_name,
                        language_code=lang_codes,
                        claim_type="l4b_semantic",
                        claim_text=f"Semantic prose parity for section '{sid}'",
                        verified=False,
                        status="pending",
                        verification_source="heuristic",
                        detail=(
                            "Semantic prose parity across languages is not "
                            "mechanically provable; reserved for LLM Auditor review"
                        ),
                        review_item_id=f"L4b:{base_name}:{sid}",
                    )
                )

        if not l4b_checks:
            l4b_checks.append(
                VerificationCheck(
                    layer="L4",
                    target="all",
                    language_code="all",
                    claim_type="l4b_semantic",
                    claim_text="Semantic prose parity across languages",
                    verified=False,
                    status="pending",
                    verification_source="heuristic",
                    detail=(
                        "Semantic prose parity is not mechanically provable; "
                        "reserved for LLM Auditor review"
                    ),
                    review_item_id="L4b:all:semantic-prose-parity",
                )
            )
        return l4b_checks

    @staticmethod
    def _concat_documents(
        documents: dict[str, list[DocumentArtifact]],
    ) -> dict[str, str]:
        """Concatenate each language's documents into one text blob."""
        return {
            lang: "\n".join(doc.content for doc in doc_list)
            for lang, doc_list in documents.items()
        }

    def _untagged_block_checks(
        self,
        documents: dict[str, list[DocumentArtifact]],
        languages: list[str],
    ) -> list[VerificationCheck]:
        """Emit L4a checks for every untagged TECHNICAL fenced code block.

        A technical fence (bash/json/yaml/…) without a ``[[id:...]]`` marker
        would silently bypass stable-ID parity, so it is a mechanical FAILURE.
        A technical block carrying an explicit ``[[parity:ignore reason="..."]]``
        marker is exempted: it is reported as ``passed`` (explicitly exempted),
        never as a failure.
        """
        checks: list[VerificationCheck] = []
        for lang in sorted(languages):
            for ref in _scan_blocks(self._concat_documents(documents)[lang], lang):
                if not ref.is_technical or ref.block_id:
                    continue
                if ref.exempted:
                    checks.append(
                        VerificationCheck(
                            layer="L4",
                            target="untagged",
                            language_code=lang,
                            claim_type="l4a_mechanical",
                            claim_text=(
                                f"Technical code block ({ref.full_block.splitlines()[0].strip()}) "
                                "is exempted from parity"
                            ),
                            verified=True,
                            status="passed",
                            verification_source="cross_language_analyzer",
                            detail=(
                                "Technical fence carries an explicit [[parity:ignore ...]] "
                                "marker, so it is exempted from stable-ID parity"
                            ),
                        )
                    )
                    continue
                lang_tag = ref.full_block.splitlines()[0].strip().lstrip("`")
                checks.append(
                    VerificationCheck(
                        layer="L4",
                        target="untagged",
                        language_code=lang,
                        claim_type="l4a_mechanical",
                        claim_text=(
                            f"Untagged technical code block ({lang_tag or 'code'}) "
                            "cannot participate in stable-ID parity"
                        ),
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            "A technical fence without a [[id:...]] marker would silently "
                            "bypass cross-language parity; tag it with a stable ID or exempt "
                            "it with [[parity:ignore reason=\"...\"]]"
                        ),
                        suggested_fix=(
                            'Add [[id:<slug>]] before the fence, or add [[parity:ignore '
                            'reason="..."]], to make parity auditable'
                        ),
                    )
                )
        return checks

    @staticmethod
    def _stable_block_parity_checks(
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[VerificationCheck]:
        """Compare ID-tagged code blocks across languages by stable ID + hash.

        Blocks are paired by ``(document_id, section_id, block_id)`` via
        ``pair_blocks_by_section_id`` so identical semantics match regardless of
        heading position / section order. A block missing from a language that
        declares the SAME document fails parity; a block in a different document
        (even with the same ``block_id``) is NOT treated as a match.
        """
        paired = pair_blocks_by_section_id(documents)

        # base_name -> set of languages that declare that document.
        doc_languages: dict[str, set[str]] = {}
        for lang, doc_list in documents.items():
            for doc in doc_list:
                doc_languages.setdefault(doc.base_name, set()).add(lang)

        results: list[VerificationCheck] = []
        for (doc_id, section_id, block_id), lang_refs in sorted(paired.items()):
            present = set(lang_refs.keys())
            expected = doc_languages[doc_id]
            target = f"{doc_id} [[id:{block_id}]]" + (
                f" @{section_id}" if section_id else ""
            )
            if len(present) < len(expected):
                missing = sorted(expected - present)
                results.append(
                    VerificationCheck(
                        layer="L4",
                        target=target,
                        language_code=",".join(missing),
                        claim_type="l4a_mechanical",
                        claim_text=f"Stable block '{block_id}' missing from {missing}",
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            f"ID-tagged block '{block_id}' (document '{doc_id}', section "
                            f"'{section_id}') present in {sorted(present)} but missing from "
                            f"{missing}"
                        ),
                        suggested_fix="Ensure each language carries the same ID-tagged code block",
                    )
                )
                continue

            hashes = {lang: lang_refs[lang].content_hash for lang in present}
            if len(set(hashes.values())) > 1:
                results.append(
                    VerificationCheck(
                        layer="L4",
                        target=target,
                        language_code="all",
                        claim_type="l4a_mechanical",
                        claim_text=f"Stable block '{block_id}' body diverges across languages",
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            f"Code in block '{block_id}' (document '{doc_id}', section "
                            f"'{section_id}') differs across languages after normalization "
                            "(SHA256 mismatch)"
                        ),
                        suggested_fix="Harmonize the ID-tagged code block so bodies match byte-for-byte",
                    )
                )
                continue

            results.append(
                VerificationCheck(
                    layer="L4",
                    target=target,
                    language_code="all",
                    claim_type="l4a_mechanical",
                    claim_text=f"Stable block '{block_id}' identical across languages",
                    verified=True,
                    status="passed",
                    verification_source="cross_language_analyzer",
                    detail=(
                        f"ID-tagged block '{block_id}' (document '{doc_id}', section "
                        f"'{section_id}') matches byte-for-byte in all languages"
                    ),
                )
            )
        return results
