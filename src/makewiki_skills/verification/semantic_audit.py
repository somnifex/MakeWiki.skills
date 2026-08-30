"""Machine-consumable SemanticAuditBundle for LLM semantic verdicts (L3/L4b/L5).

MakeWiki runs on two planes separated by a Cognitive Authority Boundary. The
semantic verifier layers (L3 behavior meaning, L4b semantic parity, L5
epistemic standing) are decided by the LLM Auditor, not by mechanical code.
This module is the *weak* Python side of that boundary: it defines a stable,
machine-readable bundle that the Auditor's verdicts are persisted into, and it
provides digest binding so a stale audit (audited against documents or a
semantic model that have since changed) can be detected and rejected.

This module deliberately performs NO semantic re-judgment. It validates schema
and digests and aggregates, but it never decides whether the Auditor's
`passed`/`failed` verdict is reasonable. A layer the Auditor did not mention
simply remains pending at the Quality Gate.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SemanticAuditLayer = Literal["L3", "L4b", "L5"]

# The LLM Auditor never emits a mechanical "pending": a layer not mentioned in
# the bundle stays pending (i.e. not proven) at the gate *by absence*, never by
# an explicit value. This status only covers the two states the Auditor may
# actually emit.
SemanticAuditStatus = Literal["passed", "failed"]


class SemanticAuditVerdict(BaseModel):
    """A single semantic verdict emitted by the LLM Auditor for one review item."""

    review_item_id: str  # e.g. "L3:workflow.start-server"
    layer: SemanticAuditLayer
    status: SemanticAuditStatus
    rationale_summary: str
    evidence_refs: list[str] = Field(default_factory=list)  # e.g. "src/app/cli.py:120-148"
    confidence: Literal["high", "medium", "low"] = "medium"


class SemanticAuditBundle(BaseModel):
    """Machine-consumable bundle capturing the Auditor's semantic verdicts.

    The `documents_digest` binds the audit to the exact markdown document set it
    was performed against, so a bundle produced against an older revision can be
    detected as stale. `semantic_model_digest` optionally binds it to the
    semantic model snapshot (via `compute_content_digest` over a model dump).
    """

    schema_version: str = "1"
    documents_digest: str  # "sha256:<hex>" over the audited document set
    semantic_model_digest: str | None = None
    auditor: str = "llm_auditor"
    audited_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    verdicts: list[SemanticAuditVerdict] = Field(default_factory=list)


class StaleAuditError(ValueError):
    """Raised when an audit bundle's digest no longer matches the verified documents."""


def _sha256_of_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def compute_content_digest(text: str) -> str:
    """sha256 of a given string content, returned as ``"sha256:<hex>"``.

    Useful for the `semantic_model_digest` from a model's serialized dump.
    """
    return _sha256_of_bytes(text.encode("utf-8"))


def compute_documents_digest(doc_paths: Iterable[Path] | Sequence[str]) -> str:
    """sha256 over the concatenated, sorted-by-path raw bytes of each document.

    Deterministic regardless of the order paths are supplied: paths are
    normalized to ``str`` and sorted before the bytes are read and hashed.
    """
    paths = [Path(p) for p in doc_paths]
    keyed: list[tuple[str, bytes]] = []
    for path in paths:
        keyed.append((str(path), path.read_bytes()))
    keyed.sort(key=lambda item: item[0])
    return _sha256_of_bytes(b"".join(raw for _, raw in keyed))


def load_audit_bundle(path: str | Path) -> SemanticAuditBundle:
    """Load and pydantic-validate an audit bundle from a JSON file.

    Raises:
        ValueError: if the file cannot be read or does not conform to the
            ``SemanticAuditBundle`` schema.
    """
    import json

    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:  # file missing / unreadable
        raise ValueError(f"Cannot read audit bundle at {path!r}: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Audit bundle at {path!r} is not valid JSON: {exc}") from exc

    try:
        return SemanticAuditBundle.model_validate(data)
    except Exception as exc:  # pydantic ValidationError or others on invalid shape
        raise ValueError(
            f"Audit bundle at {path!r} does not match SemanticAuditBundle schema: {exc}"
        ) from exc


def bundle_matches_documents(
    bundle: SemanticAuditBundle,
    doc_paths: Sequence[str] | Iterable[Path],
) -> bool:
    """True iff the bundle's documents digest equals the digest of `doc_paths`."""
    return bundle.documents_digest == compute_documents_digest(doc_paths)


def is_stale(
    bundle: SemanticAuditBundle,
    doc_paths: Sequence[str] | Iterable[Path],
    *,
    semantic_model_digest: str | None = None,
) -> bool:
    """True when the audit no longer matches what it claims to have verified.

    The bundle is stale if the documents digest mismatches the current
    documents, OR (when `semantic_model_digest` is supplied and the bundle
    carries one) if the model digest mismatches. A bundle with no
    `semantic_model_digest` and no documents to compare is NOT stale.
    """
    documents: list[Path] = [Path(p) for p in doc_paths]
    if documents:
        if not bundle_matches_documents(bundle, documents):
            return True

    if semantic_model_digest is not None and bundle.semantic_model_digest is not None:
        if bundle.semantic_model_digest != semantic_model_digest:
            return True

    return False


def validate_audit_bundle(
    bundle: SemanticAuditBundle,
    doc_paths: Sequence[str] | Iterable[Path],
    *,
    semantic_model_digest: str | None = None,
) -> None:
    """Raise `StaleAuditError` when the bundle's digest no longer matches.

    Raises:
        StaleAuditError: if `bundle` is stale against the given documents /
            semantic model digest.
    """
    if is_stale(bundle, doc_paths, semantic_model_digest=semantic_model_digest):
        raise StaleAuditError(
            "Audit bundle is stale: its digest no longer matches the verified "
            "documents or semantic model."
        )
