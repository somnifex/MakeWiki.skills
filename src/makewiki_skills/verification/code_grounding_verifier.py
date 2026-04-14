"""Check whether document claims are backed by collected project evidence."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, computed_field

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.toolkit.markdown_tools import MarkdownTool

class GroundingClaim(BaseModel):
    """A specific verifiable claim found in a generated document."""

    claim_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    document: str
    language_code: str
    claim_text: str
    claim_type: str  # "command" | "config_key" | "path" | "version"

class GroundingViolation(BaseModel):
    """A claim that cannot be grounded in project evidence."""

    claim: GroundingClaim
    violation_type: str  # "ungrounded" | "contradicted" | "low_confidence"
    message: str
    suggested_fix: str | None = None

class GroundingReport(BaseModel):
    """Result of code-grounding verification across all documents."""

    report_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_claims: int = 0
    grounded_claims: int = 0
    violations: list[GroundingViolation] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def grounding_score(self) -> float:
        if self.total_claims == 0:
            return 1.0
        return round(self.grounded_claims / self.total_claims, 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def passed(self) -> bool:
        return not any(v.violation_type == "contradicted" for v in self.violations)

class CodeGroundingVerifier:
    """Verify that document claims are grounded in collected project evidence.

    Commands, config keys, and file paths are checked against the
    evidence registry before the docs are accepted as grounded.
    """

    def __init__(self, evidence_registry: EvidenceRegistry) -> None:
        self._registry = evidence_registry
        self._md = MarkdownTool()

    def verify(
        self, documents: dict[str, list[GeneratedDocument]]
    ) -> GroundingReport:
        all_claims: list[GroundingClaim] = []
        violations: list[GroundingViolation] = []

        for lang, docs in documents.items():
            for doc in docs:
                claims = self._extract_claims(doc)
                all_claims.extend(claims)

        grounded = 0
        for claim in all_claims:
            violation = self._verify_claim(claim)
            if violation:
                violations.append(violation)
            else:
                grounded += 1

        return GroundingReport(
            total_claims=len(all_claims),
            grounded_claims=grounded,
            violations=violations,
        )

    def _extract_claims(self, doc: GeneratedDocument) -> list[GroundingClaim]:
        claims: list[GroundingClaim] = []
        facts = self._md.extract_facts(doc.content, doc.language_code, doc.filename)

        for cmd in facts.commands:
            claims.append(
                GroundingClaim(
                    document=doc.filename,
                    language_code=doc.language_code,
                    claim_text=cmd,
                    claim_type="command",
                )
            )

        for key in facts.config_keys:
            claims.append(
                GroundingClaim(
                    document=doc.filename,
                    language_code=doc.language_code,
                    claim_text=key,
                    claim_type="config_key",
                )
            )

        for fp in facts.file_paths:
            claims.append(
                GroundingClaim(
                    document=doc.filename,
                    language_code=doc.language_code,
                    claim_text=fp,
                    claim_type="path",
                )
            )

        return claims

    def _verify_claim(self, claim: GroundingClaim) -> GroundingViolation | None:
        """Check a single claim against the evidence registry."""
        if claim.claim_type == "command":
            return self._verify_command(claim)
        if claim.claim_type == "config_key":
            return self._verify_config_key(claim)
        if claim.claim_type == "path":
            return self._verify_path(claim)
        return None

    def _verify_command(self, claim: GroundingClaim) -> GroundingViolation | None:
        cmd_facts = self._registry.query(fact_type="command")
        for fact in cmd_facts:
            if fact.value and (
                fact.value in claim.claim_text or claim.claim_text in fact.value
            ):
                if fact.best_confidence == "low":
                    return GroundingViolation(
                        claim=claim,
                        violation_type="low_confidence",
                        message=f"Command '{claim.claim_text}' has only low-confidence evidence",
                    )
                return None

        generic_prefixes = [
            "cd ", "mkdir ", "git ", "pip install", "npm install",
            "yarn ", "python ", "node ", "cargo ", "go ",
        ]
        if any(claim.claim_text.startswith(p) for p in generic_prefixes):
            return None

        return GroundingViolation(
            claim=claim,
            violation_type="ungrounded",
            message=f"Command '{claim.claim_text}' not found in project evidence",
            suggested_fix="Verify this command exists in the project or add uncertainty language",
        )

    def _verify_config_key(self, claim: GroundingClaim) -> GroundingViolation | None:
        cfg_facts = self._registry.query(fact_type="config_key")
        for fact in cfg_facts:
            if fact.value and (
                claim.claim_text == fact.value
                or claim.claim_text in fact.value
                or fact.value.endswith(f".{claim.claim_text}")
            ):
                return None

        if re.match(r"^[A-Z][A-Z0-9_]+$", claim.claim_text):
            return None

        return GroundingViolation(
            claim=claim,
            violation_type="ungrounded",
            message=f"Config key '{claim.claim_text}' not found in project evidence",
        )

    def _verify_path(self, claim: GroundingClaim) -> GroundingViolation | None:
        path_facts = self._registry.query(fact_type="path")
        for fact in path_facts:
            if fact.value and (
                claim.claim_text == fact.value
                or claim.claim_text.lstrip("./") == fact.value
            ):
                return None

        return GroundingViolation(
            claim=claim,
            violation_type="ungrounded",
            message=f"Path '{claim.claim_text}' not found in project evidence",
        )
