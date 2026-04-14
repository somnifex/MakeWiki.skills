"""In-memory store for collected evidence facts."""

from __future__ import annotations

from makewiki_skills.toolkit.evidence import EvidenceFact

class EvidenceRegistry:
    """Store evidence facts and query them by type or confidence."""

    def __init__(self) -> None:
        self._facts: dict[str, EvidenceFact] = {}

    def add(self, fact: EvidenceFact) -> None:
        self._facts[fact.fact_id] = fact

    def add_many(self, facts: list[EvidenceFact]) -> None:
        for fact in facts:
            self.add(fact)

    def query(
        self,
        fact_type: str | None = None,
        min_confidence: str | None = None,
    ) -> list[EvidenceFact]:
        confidence_order = {"high": 0, "medium": 1, "low": 2, "inferred": 3}
        min_rank = confidence_order.get(min_confidence or "inferred", 3)
        results: list[EvidenceFact] = []
        for fact in self._facts.values():
            if fact_type and fact.fact_type != fact_type:
                continue
            if confidence_order.get(fact.best_confidence, 3) > min_rank:
                continue
            results.append(fact)
        return results

    def get_by_id(self, fact_id: str) -> EvidenceFact | None:
        return self._facts.get(fact_id)

    def all_facts(self) -> list[EvidenceFact]:
        return list(self._facts.values())

    def to_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for fact in self._facts.values():
            summary[fact.fact_type] = summary.get(fact.fact_type, 0) + 1
        return summary

    def __len__(self) -> int:
        return len(self._facts)
