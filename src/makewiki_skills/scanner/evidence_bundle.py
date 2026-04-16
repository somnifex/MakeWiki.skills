"""JSON-friendly scan result built from collected evidence."""

from __future__ import annotations

from pydantic import BaseModel, Field

from makewiki_skills.scanner.project_detector import ProjectDetectionResult
from makewiki_skills.toolkit.evidence import EvidenceFact


class EvidenceBundleDetection(BaseModel):
    """Serializable subset of ProjectDetectionResult."""

    project_type: str
    confidence: float
    project_name: str
    indicators_found: list[str] = Field(default_factory=list)


class EvidenceBundleFact(BaseModel):
    """Serializable evidence fact for JSON output."""

    fact_id: str
    claim: str
    fact_type: str
    value: str | None = None
    best_confidence: str
    evidence: list[dict[str, object]] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    """Structured scan result serialized by ``scan --format json``."""

    detection: EvidenceBundleDetection
    summary: dict[str, int] = Field(default_factory=dict)
    facts_by_type: dict[str, list[EvidenceBundleFact]] = Field(default_factory=dict)
    total_facts: int = 0
    files_read: list[str] = Field(default_factory=list)
    commands_discovered: list[str] = Field(default_factory=list)

    @classmethod
    def from_registry(
        cls,
        detection: ProjectDetectionResult,
        facts: list[EvidenceFact],
        files_read: list[str] | None = None,
    ) -> EvidenceBundle:
        grouped: dict[str, list[EvidenceBundleFact]] = {}
        summary: dict[str, int] = {}
        commands: list[str] = []

        for fact in facts:
            summary[fact.fact_type] = summary.get(fact.fact_type, 0) + 1

            bundle_fact = EvidenceBundleFact(
                fact_id=fact.fact_id,
                claim=fact.claim,
                fact_type=fact.fact_type,
                value=fact.value,
                best_confidence=fact.best_confidence,
                evidence=[
                    {
                        "source_path": link.source_path,
                        "line_range": link.line_range,
                        "section": link.section,
                        "raw_text": link.raw_text,
                        "confidence": link.confidence,
                        "extraction_method": link.extraction_method,
                    }
                    for link in fact.evidence
                ],
            )
            grouped.setdefault(fact.fact_type, []).append(bundle_fact)

            if fact.fact_type == "command" and fact.value:
                commands.append(fact.value)

        det = EvidenceBundleDetection(
            project_type=detection.project_type.value,
            confidence=detection.confidence,
            project_name=detection.project_name,
            indicators_found=detection.indicators_found,
        )

        return cls(
            detection=det,
            summary=summary,
            facts_by_type=grouped,
            total_facts=len(facts),
            files_read=files_read or [],
            commands_discovered=commands,
        )
