"""L4 Cross-Language Verifier: mechanical code-block parity + semantic prose parity.

L4 is split into two sub-reports:

* **L4a (mechanical)** — Python can prove this deterministically:
  - fact-delta parity (commands / config keys present in one language but not
    another), and
  - stable-block-ID SHA256 parity: code blocks tagged with ``[[id:...]]`` are
    matched across languages by their ID (never by position) and compared by a
    SHA256 of the normalized body. Identical bodies pass, diverged bodies fail,
    and a block missing from a language fails (the mechanical harmonizer could
    not prove it is the same logical block).
  L4a checks are emitted with ``claim_type="l4a_mechanical"`` and may be passed.

* **L4b (semantic)** — prose parity is *meaning*, which Python cannot judge. It
  always emits a single ``pending`` check reserved for the LLM Auditor, so the
  layer never reports a vacuous ``passed`` on semantics alone.
  L4b checks are emitted with ``claim_type="l4b_semantic"``.
"""

from __future__ import annotations

import hashlib
import re

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer
from makewiki_skills.verification.report import LayerReport, VerificationCheck

_BLOCK_ID_PATTERN = re.compile(r"\[\[id:([A-Za-z0-9_.\-]+)\]\]")
_CODE_BLOCK_PATTERN = re.compile(
    r"```(?P<lang>[a-zA-Z0-9_\-\+]*)\n(?P<code>.*?)```", re.DOTALL
)


def stable_block_content_hash(code: str) -> str:
    """Stable SHA256-derived content hash of a code block body (16 hex chars).

    Mirrors the mechanical harmonizer's ``_content_hash`` so L4 parity and the
    revision engine agree on block identity.
    """
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def extract_blocks_by_id(content: str) -> dict[str, tuple[str, str]]:
    """Map each stable block ID to its ``(full_block_text, content_hash)``.

    The ID marker may precede the fence or be the first line inside the fence
    body — the same scheme the revision engine's harmonizer uses.
    """
    blocks: dict[str, tuple[str, str]] = {}
    lines = content.splitlines(keepends=True)
    i = 0
    pending_id: str | None = None
    while i < len(lines):
        line = lines[i]
        id_match = _BLOCK_ID_PATTERN.search(line)
        if id_match:
            pending_id = id_match.group(1)
            i += 1
            continue
        if line.lstrip().startswith("```") and pending_id is not None:
            block_lines: list[str] = []
            start = i - 1 if (i - 1) >= 0 and _BLOCK_ID_PATTERN.search(lines[i - 1]) else i
            if start == i - 1:
                block_lines.append(lines[i - 1])
            block_lines.append(line)
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                block_lines.append(lines[j])
                j += 1
            if j < len(lines):
                block_lines.append(lines[j])
                j += 1
            full_block = "".join(block_lines)
            code_match = _CODE_BLOCK_PATTERN.search(full_block)
            code_body = code_match.group("code") if code_match else ""
            blocks[pending_id] = (full_block, stable_block_content_hash(code_body))
            i = j
            pending_id = None
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
                    )
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

        # ---- L4a mechanical: stable-block-ID SHA256 parity -------------------
        checks.extend(self._stable_block_parity_checks(documents, languages))

        # ---- L4b semantic: prose parity is reserved for the LLM Auditor ------
        # Python cannot judge whether translated prose carries the same meaning.
        # Emit a single honest pending check so the layer never auto-passes on
        # semantics alone.
        checks.append(
            VerificationCheck(
                layer="L4",
                target="all",
                language_code="all",
                claim_type="l4b_semantic",
                claim_text="Semantic prose parity across languages",
                verified=False,
                status="pending",
                verification_source="heuristic",
                detail="Semantic prose parity is not mechanically provable; reserved for LLM Auditor review",
            )
        )

        return LayerReport(
            layer="L4",
            name="Cross-Language",
            checks=checks,
        )

    def _stable_block_parity_checks(
        self,
        documents: dict[str, list[DocumentArtifact]],
        languages: list[str],
    ) -> list[VerificationCheck]:
        """Compare ID-tagged code blocks across languages by stable ID + hash."""
        per_lang: dict[str, dict[str, tuple[str, str]]] = {}
        for lang in languages:
            blocks: dict[str, tuple[str, str]] = {}
            for doc in documents.get(lang, []):
                blocks.update(extract_blocks_by_id(doc.content))
            per_lang[lang] = blocks

        all_ids: set[str] = set()
        for blocks in per_lang.values():
            all_ids.update(blocks.keys())

        results: list[VerificationCheck] = []
        for block_id in sorted(all_ids):
            present = {lang for lang, blocks in per_lang.items() if block_id in blocks}
            if len(present) < len(languages):
                missing = [lang for lang in languages if lang not in present]
                results.append(
                    VerificationCheck(
                        layer="L4",
                        target=f"[[id:{block_id}]]",
                        language_code=",".join(missing),
                        claim_type="l4a_mechanical",
                        claim_text=f"Stable block '{block_id}' missing from {missing}",
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            f"ID-tagged block '{block_id}' present in {sorted(present)} "
                            f"but missing from {missing}"
                        ),
                        suggested_fix="Ensure each language carries the same ID-tagged code block",
                    )
                )
                continue

            hashes = {lang: per_lang[lang][block_id][1] for lang in present}
            if len(set(hashes.values())) > 1:
                results.append(
                    VerificationCheck(
                        layer="L4",
                        target=f"[[id:{block_id}]]",
                        language_code="all",
                        claim_type="l4a_mechanical",
                        claim_text=f"Stable block '{block_id}' body diverges across languages",
                        verified=False,
                        status="failed",
                        verification_source="cross_language_analyzer",
                        detail=(
                            f"Code in block '{block_id}' differs across languages after "
                            f"normalization (SHA256 mismatch)"
                        ),
                        suggested_fix="Harmonize the ID-tagged code block so bodies match byte-for-byte",
                    )
                )
                continue

            results.append(
                VerificationCheck(
                    layer="L4",
                    target=f"[[id:{block_id}]]",
                    language_code="all",
                    claim_type="l4a_mechanical",
                    claim_text=f"Stable block '{block_id}' identical across languages",
                    verified=True,
                    status="passed",
                    verification_source="cross_language_analyzer",
                    detail=f"ID-tagged block '{block_id}' matches byte-for-byte in all languages",
                )
            )
        return results
