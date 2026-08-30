"""Verification Orchestrator: Coordinates multi-layer L0-L5 verification."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.verification.l0_syntax import L0SyntaxVerifier
from makewiki_skills.verification.l1_existence import L1ExistenceVerifier
from makewiki_skills.verification.l2_interface import L2InterfaceVerifier
from makewiki_skills.verification.l3_behavior import L3BehaviorVerifier
from makewiki_skills.verification.l4_cross_language import L4CrossLanguageVerifier
from makewiki_skills.verification.l5_epistemic import L5EpistemicVerifier
from makewiki_skills.verification.report import (
    ComprehensiveVerificationReport,
    LayerReport,
    ReviewItem,
    VerificationCheck,
)
from makewiki_skills.verification.semantic_audit import SemanticAuditBundle


def _slug(text: str) -> str:
    """Deterministic whitespace-collapsed slug of ``text`` for stable identities."""
    return " ".join(text.split())


def _section_from_review_item_id(review_item_id: str) -> str:
    """Derive a human section label from a review item id's trailing sub-part.

    Deterministic and stable: the id is split on ``:``; the trailing sub-part
    (after the layer and the document) becomes the section label. When fewer
    than three parts exist the label is the whole id after the layer.
    """
    parts = review_item_id.split(":")
    if len(parts) >= 3:
        return ":".join(parts[2:])
    if len(parts) >= 2:
        return parts[1]
    return ""


class VerificationOrchestrator:
    """Orchestrates comprehensive multi-layer (L0 - L5) grounding verification."""

    def __init__(
        self,
        project_dir: Path,
        registry: EvidenceRegistry | None = None,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.registry = registry or EvidenceRegistry()

        self.l0 = L0SyntaxVerifier()
        self.l1 = L1ExistenceVerifier(self.project_dir)
        self.l2 = L2InterfaceVerifier(self.project_dir)
        self.l3 = L3BehaviorVerifier(self.project_dir)
        self.l4 = L4CrossLanguageVerifier()
        self.l5 = L5EpistemicVerifier(registry=self.registry, project_dir=self.project_dir)

    def verify_documents(
        self,
        documents: dict[str, list[DocumentArtifact]],
        wiki_dir: Path | None = None,
        semantic_bundle: SemanticAuditBundle | None = None,
        *,
        semantic_model_digest: str | None = None,
    ) -> ComprehensiveVerificationReport:
        """Run all L0-L5 verification layers on rendered documentation.

        When ``semantic_bundle`` is provided, the LLM Auditor's verdicts for
        L3/L4b/L5 are merged INTO the report as authoritative (``passed`` /
        ``failed``) rather than left pending. This orchestrator never re-judges
        an LLM verdict — it only copies the LLM's stated status. Layers the
        bundle does not mention stay pending.

        The merge is ITEM-LEVEL: each verdict adjudicates exactly one review
        item by ``review_item_id``; unmentioned pending items stay pending; a
        verdict for an unknown ``review_item_id`` rejects the whole bundle
        (never merged).

        ``semantic_model_digest`` (optional) is the digest of the SEPARATE
        authoritative SemanticModel the bundle claims to have been audited
        against. When the bundle declares a ``semantic_model_digest`` AND a
        current digest is supplied, a mismatch makes the whole bundle STALE and
        it is rejected (never merged), so the stale semantic content cannot mark
        L3/L4b/L5 passed. When no current model digest is available the
        document-digest staleness guard still applies; the model binding simply
        cannot be proven here.
        """
        r0 = self.l0.verify_documents(documents, base_dir=wiki_dir)
        r1 = self.l1.verify_documents(documents)
        r2 = self.l2.verify_documents(documents)
        r3 = self.l3.verify_documents(documents)
        r4 = self.l4.verify_documents(documents)
        r5 = self.l5.verify_documents(documents)

        layers: dict[str, LayerReport] = {
            "L0": r0,
            "L1": r1,
            "L2": r2,
            "L3": r3,
            "L4": r4,
            "L5": r5,
        }

        report = ComprehensiveVerificationReport(layers=layers)
        if semantic_bundle is not None:
            # Staleness guard (governance): the document-digest half is enforced
            # at the call site (the CLI rejects a doc-mismatched bundle before
            # it ever reaches here). The semantic-model half is enforced here.
            # Build the item-level registry FIRST so the merge only ever
            # adjudicates items Python has actually computed.
            report.review_items = self._build_review_items(report)
            if semantic_bundle.semantic_model_digest:
                # The bundle binds to a semantic model snapshot but no current
                # model digest is provable here -> the binding is UNPROVEN. Per
                # the honesty policy the bundle is never silently trusted:
                # reject it so L3/L4b/L5 stay pending.
                if semantic_model_digest is None:
                    return report  # UNPROVEN -> reject (not merged)
                if semantic_bundle.semantic_model_digest != semantic_model_digest:
                    return report  # STALE -> reject
            self._merge_semantic_bundle(report, semantic_bundle)
        return report

    @staticmethod
    def _build_review_items(
        report: ComprehensiveVerificationReport,
    ) -> list[ReviewItem]:
        """Compute the registry of expected semantic review items from L3/L4b/L5.

        Scans the L3/L4/L5 layers' checks; for each check with
        ``status == "pending"`` and a non-None ``review_item_id`` it builds a
        ``ReviewItem``. A pending semantic check without a ``review_item_id``
        still gets a deterministic fallback id (derived from its layer + target),
        never a random one, so it remains adjudicable.
        """
        items: list[ReviewItem] = []
        layer_meta = {
            "L3": "L3",
            "L5": "L5",
        }
        for layer_name, lr in report.layers.items():
            if layer_name not in ("L3", "L4", "L5"):
                continue
            for check in lr.checks:
                if check.status != "pending":
                    continue
                layer = layer_meta.get(layer_name, layer_name)
                if layer_name == "L4":
                    # Only the semantic (L4b) sub-layer registers review items.
                    if check.claim_type != "l4b_semantic":
                        continue
                    layer = "L4b"
                rid = VerificationOrchestrator._effective_review_item_id(
                    layer_name, check
                )
                section = _section_from_review_item_id(rid)
                items.append(
                    ReviewItem(
                        review_item_id=rid,
                        layer=layer,
                        document=check.target,
                        section=section,
                        evidence=list(getattr(check, "evidence_refs", None) or []),
                        status="pending",
                    )
                )
        return items

    @staticmethod
    def _effective_review_item_id(
        layer_name: str, check: VerificationCheck
    ) -> str:
        """Return the deterministic review-item identity for a semantic check.

        Uses the check's own ``review_item_id`` when present; otherwise computes
        the same deterministic fallback the registry uses (never random) from
        the semantic layer label + target + collapsed claim text. L4 checks map
        to the ``L4b`` label to keep the bundle's ``L4b:...`` id grammar.
        """
        if check.review_item_id is not None:
            return check.review_item_id
        layer_label = "L4b" if layer_name == "L4" else layer_name
        return f"{layer_label}:{check.target}:{_slug(check.claim_text)}"

    @staticmethod
    def _merge_semantic_bundle(
        report: ComprehensiveVerificationReport,
        bundle: SemanticAuditBundle,
    ) -> None:
        """Merge the Auditor's L3/L4b/L5 verdicts into the report item-level.

        Each ``SemanticAuditVerdict`` maps to EXACTLY ONE ``VerificationCheck``
        by its ``review_item_id``. Mechanics:

        1. Build a per-layer lookup ``review_item_id -> check`` over the L3/L4b/
           L5 semantic checks that carry a non-None ``review_item_id``.
        2. For each verdict whose ``review_item_id`` matches NO existing check,
           the whole bundle is REJECTED: the merge aborts immediately, nothing is
           merged, and all L3/L4b/L5 checks stay pending. Unknown ids are
           recorded on ``report.details`` for diagnosis.
        3. Each matched verdict updates ONLY that one check in place — status,
           verified, verification source, and provenance (rationale / auditor /
           confidence / evidence / audited_at) — while preserving the check's
           ``review_item_id``.
        4. Never rebuild ``lr.checks`` wholesale; never touch L0/L1/L2/L4a
           mechanical checks; unmentioned pending checks keep ``status="pending"``.
        """
        # ---- 1. per-layer lookup -------------------------------------------
        # Build the lookup over the SAME effective review_item_id the registry
        # computed in ``_build_review_items`` (a check's own id, or the
        # deterministic fallback), so the merge adjudicates the registry's items.
        semantic_layers = {"L3", "L4", "L5"}
        lookup: dict[str, VerificationCheck] = {}
        for layer_name, lr in report.layers.items():
            if layer_name not in semantic_layers:
                continue
            for check in lr.checks:
                rid = VerificationOrchestrator._effective_review_item_id(
                    layer_name, check
                )
                lookup.setdefault(rid, check)

        # ---- 2. unknown review_item_id -> reject whole bundle --------------
        unknown_ids = [
            v.review_item_id
            for v in bundle.verdicts
            if v.review_item_id not in lookup
        ]
        if unknown_ids:
            details = dict(report.details)
            details["semantic_bundle_rejected"] = True
            details["semantic_bundle_rejection_reason"] = "unknown_review_item_id"
            details["semantic_bundle_unknown_ids"] = sorted(set(unknown_ids))
            report.details = details
            return  # rejected: nothing merged, L3/L4b/L5 stay pending

        # ---- 3. item-level update for each matched verdict -----------------
        for verdict in bundle.verdicts:
            check = lookup[verdict.review_item_id]
            check.status = verdict.status
            check.verified = verdict.status == "passed"
            check.verification_source = "semantic_audit_bundle"
            # Preserve semantic content + provenance on the merged check.
            provenance = (
                f"LLM Auditor: {bundle.auditor}; rationale: {verdict.rationale_summary}"
                f"; confidence: {verdict.confidence}"
                f"; evidence: {', '.join(verdict.evidence_refs) if verdict.evidence_refs else 'none'}"
                f"; audited_at: {bundle.audited_at} | {check.detail}"
            )
            check.detail = provenance

    def verify_layer(
        self,
        layer: str,
        documents: dict[str, list[DocumentArtifact]],
        wiki_dir: Path | None = None,
    ) -> LayerReport:
        """Run a single specific verification layer (e.g. 'L0', 'L1', 'L2')."""
        norm_layer = layer.upper()
        if norm_layer == "L0":
            return self.l0.verify_documents(documents, base_dir=wiki_dir)
        elif norm_layer == "L1":
            return self.l1.verify_documents(documents)
        elif norm_layer == "L2":
            return self.l2.verify_documents(documents)
        elif norm_layer == "L3":
            return self.l3.verify_documents(documents)
        elif norm_layer == "L4":
            return self.l4.verify_documents(documents)
        elif norm_layer == "L5":
            return self.l5.verify_documents(documents)
        else:
            raise ValueError(f"Unknown verification layer: {layer}. Must be L0-L5.")
