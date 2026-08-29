"""Verification Orchestrator: Coordinates multi-layer L0-L5 verification."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
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
        documents: dict[str, list[GeneratedDocument]],
        wiki_dir: Path | None = None,
    ) -> ComprehensiveVerificationReport:
        """Run all L0-L5 verification layers on rendered documentation."""
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

        return ComprehensiveVerificationReport(layers=layers)

    def verify_layer(
        self,
        layer: str,
        documents: dict[str, list[GeneratedDocument]],
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
