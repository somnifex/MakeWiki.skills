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
  Block/product identity is keyed on STABLE IDs — section markers
  (``<!-- makewiki:section=<slug> -->``) and ``[[id:...]]`` block IDs — never on
  heading text or heading position, because languages may legitimately reorder
  their sections.
  L4a checks are emitted with ``claim_type="l4a_mechanical"`` and may be passed.

* **L4b (semantic)** — prose parity is *meaning*, which Python cannot judge. It
  always emits a single ``pending`` check reserved for the LLM Auditor, so the
  layer never reports a vacuous ``passed`` on semantics alone.
  L4b checks are emitted with ``claim_type="l4b_semantic"``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer
from makewiki_skills.verification.report import LayerReport, VerificationCheck

_BLOCK_ID_PATTERN = re.compile(r"\[\[id:([A-Za-z0-9_.\-]+)\]\]")
_PARITY_IGNORE_PATTERN = re.compile(r"\[\[parity:ignore(?:[^\]]*)\]\]")
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

    @property
    def stable_key(self) -> tuple[str, str]:
        """(section_id, block_id) pair used to match a block across languages."""
        return (self.section_id, self.block_id)


def stable_block_content_hash(code: str) -> str:
    """Stable SHA256-derived content hash of a code block body (16 hex chars).

    Mirrors the mechanical harmonizer's ``_content_hash`` so L4 parity and the
    revision engine agree on block identity.
    """
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def render_section_marker(slug: str) -> str:
    """Render the stable section marker for ``slug``.

    Returns ``<!-- makewiki:section=<slug> -->`` exactly. ``slug`` is emitted
    verbatim; callers are responsible for passing a slug that matches the
    ``[A-Za-z0-9_.\\-]+`` grammar ``section_ids`` accepts.
    """
    return f"<!-- makewiki:section={slug} -->"


def section_ids(doc: str) -> list[str]:
    """Return the ordered list of stable section IDs declared in ``doc``.

    Sections are declared with ``<!-- makewiki:section=<slug> -->`` markers.
    The order is the order the markers appear in the document.
    """
    return _SECTION_MARKER_PATTERN.findall(doc)


def split_sections(doc: str) -> list[tuple[str, str]]:
    """Split ``doc`` into ``(section_id, content)`` chunks by section markers.

    The marker line itself is removed from the chunk. When ``doc`` declares no
    section markers, a single ``("", doc)`` chunk is returned so callers can
    fall back to pairing by block ID alone.
    """
    markers = list(_SECTION_MARKER_PATTERN.finditer(doc))
    if not markers:
        return [("", doc)]
    chunks: list[tuple[str, str]] = []
    for idx, m in enumerate(markers):
        start = m.end()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(doc)
        chunks.append((m.group(1), doc[start:end]))
    return chunks


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
    documents: dict[str, str],
) -> dict[tuple[str, str], dict[str, BlockRef]]:
    """Group fenced+tagged blocks by (section_id, block_id) across languages.

    **Stable public data contract** (consumed by the orchestrator / CLI):

    ``documents`` maps a language code to the concatenated document text for
    that language.

    Returns a deterministic mapping ``{(section_id, block_id): {language: BlockRef}}``.
    A block is included only if it carries a stable ``[[id:...]]`` marker; the
    section key is the nearest preceding ``<!-- makewiki:section=<slug> -->``
    marker. Matching is therefore keyed on stable identity (section + block ID),
    never on heading text or heading position — languages may reorder sections
    and the same block still pairs correctly.

    **Fallback**: if ANY language document declares no section markers, pairing
    falls back to matching tagged blocks by ``block_id`` alone (section key is
    ``""`` for every block), so parity still works for un-marked documents.

    The mapping is deterministic: languages and blocks are visited in sorted
    order and every language present for a given (section, block) key appears in
    the inner dict (at most one ``BlockRef`` per language per key).
    """
    use_sections = all(bool(_SECTION_MARKER_PATTERN.search(c)) for c in documents.values())
    paired: dict[tuple[str, str], dict[str, BlockRef]] = {}
    for lang in sorted(documents):
        for ref in _scan_blocks(documents[lang], lang):
            if not ref.block_id:
                continue
            key_section = ref.section_id if use_sections else ""
            key = (key_section, ref.block_id)
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
        if len(languages) < 2:
            # With a single language there is nothing to compare for parity, so
            # cross-language verification is genuinely not applicable. It must
            # never be reported as "passed" - no parity check actually ran.
            return LayerReport(
                layer="L4",
                name="Cross-Language",
                checks=[
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
                    ),
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
                    ),
                ],
            )

        checks: list[VerificationCheck] = []

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
        checks.extend(self._stable_block_parity_checks(documents, languages))

        # ---- L4b semantic: prose parity is reserved for the LLM Auditor ------
        # Python cannot judge whether translated prose carries the same meaning.
        # Emit one honest pending check PER SECTION of each base document that
        # exists in >=2 languages, so the LLM Auditor can adjudicate prose
        # parity item-by-item. Each carries a stable, deterministic
        # ``review_item_id`` = ``L4b:<base_name>:<section_id>``. Python never
        # auto-passes on semantics alone.
        checks.extend(self._l4b_semantic_section_checks(documents))

        return LayerReport(
            layer="L4",
            name="Cross-Language",
            checks=checks,
        )

    @staticmethod
    def _l4b_semantic_section_checks(
        documents: dict[str, list[DocumentArtifact]],
    ) -> list[VerificationCheck]:
        """Emit per-section ``l4b_semantic`` pending checks for multi-language docs.

        Each base document present in >=2 languages is split into sections
        (reusing ``split_sections``); one pending l4b check is emitted per
        section, its section content across languages being the prose-parity
        passage. The section passage is keyed by a stable ``review_item_id`` of
        form ``L4b:<base_name>:<section_id>``; when a section has no marker id
        (or ids collide) a deterministic fallback keeps ids unique.

        If no base document spans >=2 languages a single synthetic pending l4b
        check is emitted so the multi-language L4 layer still carries at least
        one ``claim_type == "l4b_semantic"`` check (the Quality Gate depends on
        it) — mirroring the historical single-check behavior.
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
            sections = split_sections(lang_map[rep_lang])
            seen: set[str] = set()
            for idx, (section_id, _content) in enumerate(sections):
                sid = section_id or f"section-{idx}"
                if sid in seen:
                    sid = f"{sid}-{idx}"
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

    def _stable_block_parity_checks(
        self,
        documents: dict[str, list[DocumentArtifact]],
        languages: list[str],
    ) -> list[VerificationCheck]:
        """Compare ID-tagged code blocks across languages by stable ID + hash.

        Blocks are paired by (section_id, block_id) via ``pair_blocks_by_section_id``
        so identical semantics match regardless of heading position / section
        order. If any language declares no section markers, pairing falls back
        to block ID alone.
        """
        concatenated = self._concat_documents(documents)
        paired = pair_blocks_by_section_id(concatenated)

        results: list[VerificationCheck] = []
        for (section_id, block_id), lang_refs in sorted(paired.items()):
            present = set(lang_refs.keys())
            if len(present) < len(languages):
                missing = [lang for lang in languages if lang not in present]
                results.append(
                    VerificationCheck(
                        layer="L4",
                        target=f"[[id:{block_id}]]" + (f" @{section_id}" if section_id else ""),
                        language_code=",".join(missing),
                        claim_type="l4a_mechanical",
                        claim_text=f"Stable block '{block_id}' missing from {missing}",
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            f"ID-tagged block '{block_id}' (section '{section_id}') present in "
                            f"{sorted(present)} but missing from {missing}"
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
                        target=f"[[id:{block_id}]]" + (f" @{section_id}" if section_id else ""),
                        language_code="all",
                        claim_type="l4a_mechanical",
                        claim_text=f"Stable block '{block_id}' body diverges across languages",
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            f"Code in block '{block_id}' (section '{section_id}') differs across "
                            "languages after normalization (SHA256 mismatch)"
                        ),
                        suggested_fix="Harmonize the ID-tagged code block so bodies match byte-for-byte",
                    )
                )
                continue

            results.append(
                VerificationCheck(
                    layer="L4",
                    target=f"[[id:{block_id}]]" + (f" @{section_id}" if section_id else ""),
                    language_code="all",
                    claim_type="l4a_mechanical",
                    claim_text=f"Stable block '{block_id}' identical across languages",
                    verified=True,
                    status="passed",
                    verification_source="cross_language_analyzer",
                    detail=(
                        f"ID-tagged block '{block_id}' (section '{section_id}') matches "
                        "byte-for-byte in all languages"
                    ),
                )
            )
        return results
