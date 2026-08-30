"""Verification Orchestrator: Coordinates multi-layer L0-L5 verification."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

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
    VerificationCheck,
    VerificationStatus,
)
from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    SemanticAuditVerdict,
)


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
            # it ever reaches here). The semantic-model half is enforced here:
            # when the bundle declares a ``semantic_model_digest`` AND a current
            # model digest is supplied, a mismatch makes the bundle STALE so its
            # outdated LLM verdicts are never merged (L3/L4b/L5 stay pending).
            # Python never fabricates a model digest it cannot compute — with no
            # supplied current digest the model binding simply stays unproven.
            if (
                semantic_bundle.semantic_model_digest
                and semantic_model_digest
                and semantic_bundle.semantic_model_digest != semantic_model_digest
            ):
                return report
            self._merge_semantic_bundle(report, semantic_bundle)
        return report

    @staticmethod
    def _merge_semantic_bundle(
        report: ComprehensiveVerificationReport,
        bundle: SemanticAuditBundle,
    ) -> None:
        """Copy the Auditor's L3/L4b/L5 verdicts into the report.

        For each semantic layer the bundle carries a verdict for, the layer's
        LLM-judged pending checks are replaced with a single authoritative check
        reflecting the Auditor's stated status (``passed`` if no verdict failed,
        else ``failed``). This satisfies the re-verify contract: a valid audit
        verdict is never reset back to ``pending``. Mechanical checks (L0/L1/L2
        and L4a) are untouched.
        """
        by_layer: dict[str, list[SemanticAuditVerdict]] = {}
        for verdict in bundle.verdicts:
            by_layer.setdefault(verdict.layer, []).append(verdict)

        for layer_name, verdicts in by_layer.items():
            failed = any(v.status == "failed" for v in verdicts)
            status: Literal["passed", "failed"] = "failed" if failed else "passed"
            if layer_name == "L4b":
                VerificationOrchestrator._adjudicate_l4b(report, status)
            elif layer_name in ("L3", "L5"):
                VerificationOrchestrator._adjudicate_llm_layer(
                    report, layer_name, status
                )
            # Any other layer name in the bundle is ignored — the orchestrator
            # does not touch mechanical layers with LLM verdicts.

    @staticmethod
    def _adjudicate_l4b(
        report: ComprehensiveVerificationReport, status: VerificationStatus
    ) -> None:
        """Replace the L4 layer's LLM-judged prose-parity checks with the audit verdict."""
        l4 = report.layers.get("L4")
        if l4 is None:
            return
        # Keep the mechanical (L4a) checks; drop the semantic (L4b) pending ones
        # and replace them with a single authoritative verdict check.
        kept = [c for c in l4.checks if c.claim_type != "l4b_semantic"]
        kept.append(
            VerificationCheck(
                layer="L4",
                target="all",
                language_code="all",
                claim_type="l4b_semantic",
                claim_text="Semantic prose parity across languages (LLM Auditor)",
                verified=status == "passed",
                status=status,
                verification_source="heuristic",
                detail=(
                    "Adjudicated by the LLM Auditor"
                    if status == "passed"
                    else "Semantic prose parity was not upheld by the LLM Auditor"
                ),
            )
        )
        l4.checks = kept

    @staticmethod
    def _adjudicate_llm_layer(
        report: ComprehensiveVerificationReport,
        layer_name: str,
        status: VerificationStatus,
    ) -> None:
        """Replace an LLM layer's (L3/L5) pending checks with the audit verdict."""
        lr = report.layers.get(layer_name)
        if lr is None:
            return
        claim_type = {
            "L3": "behavior",
            "L5": "epistemic",
        }[layer_name]
        lr.checks = [
            VerificationCheck(
                layer=layer_name,
                target="all",
                claim_type=claim_type,
                claim_text=f"{layer_name} audit verdict",
                verified=status == "passed",
                status=status,
                verification_source="heuristic",
                detail=(
                    "Adjudicated by the LLM Auditor"
                    if status == "passed"
                    else f"{layer_name} was not upheld by the LLM Auditor"
                ),
            )
        ]

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
