"""Unit tests for the SemanticAuditBundle module (L3/L4b/L5 semantic audits)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    SemanticAuditVerdict,
    StaleAuditError,
    bundle_matches_documents,
    compute_content_digest,
    compute_documents_digest,
    is_stale,
    load_audit_bundle,
    validate_audit_bundle,
)


def make_bundle(digest: str, semantic_model_digest: str | None = None) -> SemanticAuditBundle:
    return SemanticAuditBundle(
        documents_digest=digest,
        semantic_model_digest=semantic_model_digest,
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:workflow.start-server",
                layer="L3",
                status="passed",
                rationale_summary="Behavior matches documented workflow.",
                evidence_refs=["src/app/cli.py:120-148"],
                confidence="high",
            ),
        ],
    )


def write_doc_world(tmp_path, contents: dict[str, str]):
    """Create document files in tmp_path and return their paths."""
    for name, content in contents.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    return [tmp_path / name for name in contents]


def test_load_audit_bundle_roundtrip(tmp_path):
    bundle = make_bundle(compute_content_digest("doc"))
    bundle_path = tmp_path / "audit.json"
    bundle_path.write_text(bundle.model_dump_json(), encoding="utf-8")

    loaded = load_audit_bundle(bundle_path)

    assert loaded == bundle
    assert loaded.schema_version == "1"
    assert loaded.auditor == "llm_auditor"
    assert loaded.documents_digest == bundle.documents_digest
    assert len(loaded.verdicts) == 1
    assert loaded.verdicts[0].review_item_id == "L3:workflow.start-server"
    assert loaded.verdicts[0].confidence == "high"
    assert loaded.audited_at is not None


def test_load_invalid_bundle_raises_invalid_json(tmp_path):
    bundle_path = tmp_path / "bad.json"
    bundle_path.write_text("{ this is not json ", encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_audit_bundle(bundle_path)
    assert "not valid JSON" in str(exc.value)


def test_load_invalid_bundle_raises_missing_digest(tmp_path):
    bundle_path = tmp_path / "bad.json"
    bundle_path.write_text(json.dumps({"schema_version": "1"}), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_audit_bundle(bundle_path)
    assert "does not match SemanticAuditBundle schema" in str(exc.value)


def test_load_invalid_bundle_raises_invalid_layer(tmp_path):
    bundle_path = tmp_path / "bad.json"
    data = {
        "documents_digest": compute_content_digest("x"),
        "verdicts": [
            {
                "review_item_id": "L9:bogus",
                "layer": "L9",
                "status": "passed",
                "rationale_summary": "nope",
            }
        ],
    }
    bundle_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        load_audit_bundle(bundle_path)
    assert "does not match SemanticAuditBundle schema" in str(exc.value)


def test_load_invalid_bundle_raises_missing_file(tmp_path):
    with pytest.raises(ValueError) as exc:
        load_audit_bundle(tmp_path / "missing.json")
    assert "Cannot read audit bundle" in str(exc.value)


def test_compute_documents_digest_deterministic(tmp_path):
    paths = write_doc_world(
        tmp_path,
        {"b.md": "# B", "a.md": "# A", "c.md": "# C"},
    )

    forward = compute_documents_digest(paths)
    reversed_ = compute_documents_digest(list(reversed(paths)))
    scattered = compute_documents_digest([paths[1], paths[2], paths[0]])

    assert forward == reversed_ == scattered
    assert forward.startswith("sha256:")
    assert len(forward) == len("sha256:") + 64


def test_compute_content_digest_deterministic():
    assert compute_content_digest("hello") == compute_content_digest("hello")
    assert compute_content_digest("hello").startswith("sha256:")
    assert compute_content_digest("hello") != compute_content_digest("world")


def test_bundle_matches_documents_true_and_false(tmp_path):
    paths = write_doc_world(tmp_path, {"doc.md": "content"})
    digest = compute_documents_digest(paths)

    bundle = make_bundle(digest)
    assert bundle_matches_documents(bundle, paths) is True

    changed = write_doc_world(tmp_path, {"doc.md": "content changed"})
    assert bundle_matches_documents(bundle, changed) is False


def test_is_stale_rejects_modified_documents(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("original", encoding="utf-8")
    digest = compute_documents_digest([doc])
    bundle = make_bundle(digest)

    # Unchanged documents -> not stale.
    assert is_stale(bundle, [doc]) is False

    # Append to the document -> digest changes -> stale.
    doc.write_text("original + more", encoding="utf-8")
    assert is_stale(bundle, [doc]) is True


def test_semantic_model_digest_mismatch_stale(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("content", encoding="utf-8")
    digest = compute_documents_digest([doc])

    bundle = make_bundle(digest, semantic_model_digest="sha256:aaaa")

    assert is_stale(bundle, [doc], semantic_model_digest="sha256:bbbb") is True
    assert is_stale(bundle, [doc], semantic_model_digest="sha256:aaaa") is False


def test_validate_raises_stale_audit_error_on_mismatch(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("original", encoding="utf-8")
    bundle = make_bundle(compute_documents_digest([doc]))

    # Fresh -> no exception.
    validate_audit_bundle(bundle, [doc])

    doc.write_text("changed", encoding="utf-8")
    with pytest.raises(StaleAuditError):
        validate_audit_bundle(bundle, [doc])

    # StaleAuditError is a ValueError subtype.
    assert issubclass(StaleAuditError, ValueError)


def test_bundle_with_no_verdicts_not_stale(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("content", encoding="utf-8")
    digest = compute_documents_digest([doc])

    empty_bundle = SemanticAuditBundle(documents_digest=digest, verdicts=[])
    assert empty_bundle.verdicts == []
    assert is_stale(empty_bundle, [doc]) is False
    validate_audit_bundle(empty_bundle, [doc])  # no exception


def test_bundle_no_documents_compared_not_stale():
    # A bundle with no semantic_model_digest and no documents to compare is not stale.
    empty_digest = compute_documents_digest([])
    bundle_no_docs = make_bundle(empty_digest)

    assert is_stale(bundle_no_docs, []) is False
    validate_audit_bundle(bundle_no_docs, [])  # no exception


def test_audited_at_defaults_to_utc(monkeypatch):
    fixed = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "makewiki_skills.verification.semantic_audit.datetime",
        _FixedDateTime(fixed),
    )
    bundle = SemanticAuditBundle(documents_digest="sha256:xxxx")
    assert bundle.audited_at == fixed.isoformat()


def test_verdict_layer_and_status_are_typed():
    with pytest.raises(ValidationError):
        SemanticAuditVerdict(
            review_item_id="x",
            layer="L7",  # invalid layer
            status="passed",
            rationale_summary="y",
        )
    with pytest.raises(ValidationError):
        SemanticAuditVerdict(
            review_item_id="x",
            layer="L3",
            status="pending",  # LLM never emits pending
            rationale_summary="y",
        )


class _FixedDateTime:
    """Stand-in for datetime returning a fixed now from `now(UTC)`."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self, tz=None) -> datetime:  # noqa: ARG002
        return self._fixed
