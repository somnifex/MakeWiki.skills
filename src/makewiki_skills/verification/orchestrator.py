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
from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    validate_bundle_shape,
)


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
        # The Review Registry is computed on EVERY verify, bundle or not. The
        # LLM Auditor's verdicts may only adjudicate items that exist here, and
        # a first run without a bundle still needs to expose the pending L3/L4b/
        # L5 items for a later audit. ``_build_review_items`` raises on a
        # duplicate ``review_item_id`` (an invariant break) rather than silently
        # collapsing two distinct semantic items into one.
        report.review_items = self._build_review_items(report)
        if semantic_bundle is not None:
            # Staleness guard (governance): the document-digest half is enforced
            # at the call site (the CLI rejects a doc-mismatched bundle before
            # it ever reaches here). The semantic-model half is enforced here.
            # The item-level registry is already computed above so the merge
            # only ever adjudicates items Python has actually computed.
            if semantic_bundle.semantic_model_digest:
                # The bundle binds to a semantic model snapshot but no current
                # model digest is provable here -> the binding is UNPROVEN. Per
                # the honesty policy the bundle is never silently trusted:
                # reject it so L3/L4b/L5 stay pending.
                if semantic_model_digest is None:
                    return report  # UNPROVEN -> reject (not merged)
                if semantic_bundle.semantic_model_digest != semantic_model_digest:
                    return report  # STALE -> reject
            # Re-validate the bundle's cross-row shape (no duplicate
            # review_item_id, layer prefix matches). Python must never merge a
            # malformed bundle — the rejection below relies on well-formed ids.
            validate_bundle_shape(semantic_bundle)
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

        The registry must hold UNIQUE ``review_item_id`` values: each stable
        identity maps to exactly one pending semantic item. A duplicate is an
        invariant break (two distinct checks silently collapsing into one — the
        same silent-overwrite failure the merge would otherwise paper over), so
        it raises ``ValueError`` instead of returning a corrupted registry.
        """
        items: list[ReviewItem] = []
        seen_ids: set[str] = set()
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
                if rid in seen_ids:
                    raise ValueError(
                        f"duplicate review_item_id {rid!r} across pending semantic "
                        f"checks in layer {layer_name!r}: the Review Registry must "
                        "hold unique stable identities (no silent dict/set merge)"
                    )
                seen_ids.add(rid)
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

        Each ``SemanticAuditVerdict`` maps to EXACTLY ONE registry item (matched
        by ``review_item_id``), and may only adjudicate an item that exists in
        the Review Registry Python computed in ``_build_review_items``. The
        registry is the authoritative, deduplicated list of pending semantic
        items (pending-only, L4b-only) — so a verdict can never adjudicate a
        check the registry did not register. Mechanics:

        1. Build a lookup ``review_item_id -> check`` over the REGISTRY items
           (mapping back to the underlying ``VerificationCheck`` by the same
           effective id the registry used).
        2. For each verdict whose ``review_item_id`` matches NO registry item,
           the whole bundle is REJECTED: nothing is merged, and all L3/L4b/L5
           checks stay pending. Unknown ids are recorded on ``report.details``
           for diagnosis. (Duplicate verdict ids are rejected earlier by
           ``validate_bundle_shape``.)
        3. Each matched verdict updates ONLY that one check in place — status,
           verified, verification source, and STRUCTURED provenance
           (auditor / rationale_summary / evidence_refs / confidence /
           audited_at, stored on ``check.provenance``) — while preserving the
           check's ``review_item_id`` and a readable ``detail``.
        4. Never rebuild ``lr.checks`` wholesale; never touch L0/L1/L2/L4a
           mechanical checks; unmentioned pending checks keep ``status="pending"``.
        """
        # ---- 1. lookup over REGISTRY items only ----------------------------
        # The registry carries the exact set of adjudicable, pending semantic
        # items. Map each registered review_item_id to its underlying
        # VerificationCheck via the effective id; the registry is already
        # deduplicated and L4b-only (see ``_build_review_items``), so a registered
        # item matches exactly one check. A second check claiming the same id
        # would be a silent-overwrite conflict, so it is rejected explicitly.
        registry_ids = {item.review_item_id for item in report.review_items}
        check_by_rid: dict[str, VerificationCheck] = {}
        for layer_name in ("L3", "L4", "L5"):
            lr = report.layers.get(layer_name)
            if lr is None:
                continue
            for check in lr.checks:
                rid = VerificationOrchestrator._effective_review_item_id(
                    layer_name, check
                )
                if rid in registry_ids:
                    if rid in check_by_rid:
                        raise ValueError(
                            f"duplicate review_item_id {rid!r} maps to more than "
                            "one VerificationCheck in the Review Registry; refusing "
                            "to silently merge one check over another"
                        )
                    check_by_rid[rid] = check

        # ---- 2. unknown review_item_id -> reject whole bundle --------------
        unknown_ids = [
            v.review_item_id
            for v in bundle.verdicts
            if v.review_item_id not in registry_ids
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
            check = check_by_rid[verdict.review_item_id]
            check.status = verdict.status
            check.verified = verdict.status == "passed"
            check.verification_source = "semantic_audit_bundle"
            # Structured provenance: the Auditor's adjudication record kept as
            # first-class fields (Python does not re-judge the verdict, it only
            # preserves who said what, when, and why).
            check.provenance = {
                "auditor": bundle.auditor,
                "rationale_summary": verdict.rationale_summary,
                "evidence_refs": list(verdict.evidence_refs),
                "confidence": verdict.confidence,
                "audited_at": bundle.audited_at,
            }
            # A readable one-line summary remains on detail for CLI/legacy
            # display; the structured fields are the source of truth.
            evidence = ", ".join(verdict.evidence_refs) if verdict.evidence_refs else "none"
            check.detail = (
                f"LLM Auditor: {bundle.auditor}; rationale: {verdict.rationale_summary}"
                f"; confidence: {verdict.confidence}"
                f"; evidence: {evidence}; audited_at: {bundle.audited_at}"
            )

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
