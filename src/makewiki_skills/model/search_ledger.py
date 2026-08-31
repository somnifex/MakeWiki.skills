"""Search Ledger Model & Markdown Parser.

Structured deliverable emitted by Scout subagents upon completing an investigation.
Acts as the auditable evidence handoff to the Main Agent for search loop evaluation.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.model.v3_artifacts import (
    Claim,
    ClaimBundle,
    ClaimEvidence,
)


class ScoutClaim(BaseModel):
    """An individual factual claim discovered by a scout."""

    claim_id: str
    description: str
    evidence_citations: list[str] = Field(default_factory=list)
    is_conflict: bool = False
    confidence: str = "high"  # high | medium | low


class SearchLedger(BaseModel):
    """Structured deliverable from a Scout subagent."""

    role: str
    searched_areas: list[str] = Field(default_factory=list)
    paths_inspected: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    claims: list[ScoutClaim] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    unexplored: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    recommended_followups: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render search ledger as structured Markdown."""
        lines = [
            "<search_ledger>",
            f"# Role: {self.role}",
            f"**Confidence:** {self.confidence:.2f}",
            "",
            "## Searched Areas",
        ]
        for area in self.searched_areas:
            lines.append(f"- {area}")

        lines.extend(["", "## Paths Inspected"])
        for path in self.paths_inspected:
            lines.append(f"- `{path}`")

        lines.extend(["", "## Claims & Evidence"])
        for idx, claim in enumerate(self.claims, start=1):
            conflict_tag = " **[CONFLICT]**" if claim.is_conflict else ""
            lines.append(f"{idx}. **[{claim.claim_id}]**{conflict_tag}: {claim.description}")
            if claim.evidence_citations:
                cites = ", ".join(f"`{c}`" for c in claim.evidence_citations)
                lines.append(f"   - *Evidence*: {cites}")

        lines.extend(["", "## Unresolved"])
        for item in self.unresolved:
            lines.append(f"- {item}")

        lines.extend(["", "## Unexplored"])
        for item in self.unexplored:
            lines.append(f"- {item}")

        lines.extend(["", "## Recommended Follow-ups"])
        for item in self.recommended_followups:
            lines.append(f"- {item}")

        lines.extend(["", "</search_ledger>"])
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SearchLedger:
        """Create SearchLedger from dictionary."""
        return cls.model_validate(data)

    def to_claim_bundle(
        self,
        bundle_id: str = "",
        domain: str = "",
        producer_subtask: str = "",
        summary: str = "",
    ) -> ClaimBundle:
        """Convert (compatibly) to a V3 :class:`ClaimBundle`.

        Only fields that map literally are migrated. ``visibility`` and
        ``abstraction`` are set to ``"unknown"`` — they are LLM classifications
        and Python must NOT infer them (``ARTIFACT_CONTRACTS`` §3). The semantic
        bundle identity fields (``bundle_id`` / ``domain`` / ``producer_subtask`` /
        ``summary``) are supplied by the caller (the Main Agent LLM), never
        guessed by Python. This does not run the Markdown parser; it only wraps
        already-parsed ledger data, so parser behavior is unchanged.

        A migrated bundle must not be a completed-empty shell: the caller must
        supply non-blank identity and summary, and there must be at least one
        claim / unresolved / recommended follow-up to migrate. If not, this raises
        a ``ValueError`` rather than emitting an artifact that would masquerade as
        a completed investigation (``ARTIFACT_CONTRACTS`` §3, V3-P1-03).
        """
        claims: list[Claim] = []
        for scout in self.claims:
            claims.append(
                Claim(
                    id=scout.claim_id,
                    statement=scout.description,
                    semantic_key=scout.claim_id,
                    confidence=scout.confidence,
                    visibility=["unknown"],
                    abstraction="unknown",
                    evidence=[
                        # Legacy citations carry only a source path, no rationale.
                        # B3 requires a non-blank rationale; Python cannot invent a
                        # semantic one, so it records a literal, neutral marker that
                        # says the citation was migrated verbatim.
                        ClaimEvidence(
                            path=cite,
                            symbol_or_location="",
                            rationale=f"legacy citation migrated verbatim: {cite}",
                        )
                        for cite in scout.evidence_citations
                    ],
                    uncertainty=None,
                )
            )
        if (
            not bundle_id.strip()
            or not domain.strip()
            or not producer_subtask.strip()
            or not summary.strip()
        ):
            raise ValueError(
                "SearchLedger.to_claim_bundle requires non-blank bundle_id, "
                "domain, producer_subtask, and summary (the Main Agent LLM must "
                "supply bundle identity; Python must not guess it)"
            )
        if not (claims or self.unresolved or self.recommended_followups):
            raise ValueError(
                "SearchLedger.to_claim_bundle has nothing to migrate (no claims, "
                "no unresolved, no recommended follow-ups) — refusing to emit an "
                "empty ClaimBundle as if investigation were complete"
            )
        return ClaimBundle(
            id=bundle_id,
            domain=domain,
            producer_subtask=producer_subtask,
            summary=summary,
            claims=claims,
            unresolved=list(self.unresolved),
            recommended_followups=list(self.recommended_followups),
        )


def parse_search_ledger_markdown(text: str) -> SearchLedger:
    """Extract and parse a `<search_ledger>` block from subagent markdown output."""
    ledger_match = re.search(r"<search_ledger>(.*?)</search_ledger>", text, re.DOTALL | re.IGNORECASE)
    content = ledger_match.group(1).strip() if ledger_match else text.strip()

    # Role
    role_match = re.search(r"#\s*Role:\s*(.+)$", content, re.MULTILINE)
    role = role_match.group(1).strip() if role_match else "Scout"

    # Confidence
    conf_match = re.search(r"\*\*Confidence:\*\*\s*([\d\.]+)", content, re.IGNORECASE)
    confidence = float(conf_match.group(1)) if conf_match else 1.0

    # Sections extraction helper
    def _extract_section_list(section_name: str) -> list[str]:
        pattern = rf"##\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##|\Z)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        sec_text = match.group(1).strip()
        items: list[str] = []
        for line in sec_text.splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                item = line[2:].strip().strip("`")
                if item:
                    items.append(item)
        return items

    searched_areas = _extract_section_list("Searched Areas")
    paths_inspected = _extract_section_list("Paths Inspected")
    unresolved = _extract_section_list("Unresolved")
    unexplored = _extract_section_list("Unexplored")
    recommended_followups = _extract_section_list("Recommended Follow-ups")

    # Parse Claims & Evidence
    claims: list[ScoutClaim] = []
    claims_match = re.search(r"##\s*Claims\s*&\s*Evidence\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    if claims_match:
        c_text = claims_match.group(1).strip()
        # Parse numbered list items
        claim_blocks = re.split(r"\n(?=\d+\.\s+)", c_text)
        for block in claim_blocks:
            block = block.strip()
            if not block:
                continue
            head_match = re.match(r"^\d+\.\s+\*\*\[([^\]]+)\]\*\*(\s*\*\*\[CONFLICT\]\*\*)?:\s*(.+)$", block.splitlines()[0])
            if head_match:
                claim_id = head_match.group(1).strip()
                is_conflict = bool(head_match.group(2))
                description = head_match.group(3).strip()
            else:
                claim_id = f"claim_{len(claims)+1}"
                is_conflict = "[CONFLICT]" in block
                description = block.splitlines()[0].strip()

            cites: list[str] = []
            cite_match = re.search(r"\*Evidence\*:\s*(.+)$", block, re.MULTILINE)
            if cite_match:
                raw_cites = cite_match.group(1)
                cites = [c.strip().strip("`") for c in re.findall(r"`([^`]+)`", raw_cites)] or [raw_cites.strip()]

            claims.append(
                ScoutClaim(
                    claim_id=claim_id,
                    description=description,
                    evidence_citations=cites,
                    is_conflict=is_conflict,
                )
            )

    evidence_refs = list({cite for c in claims for cite in c.evidence_citations})

    return SearchLedger(
        role=role,
        searched_areas=searched_areas,
        paths_inspected=paths_inspected,
        evidence_refs=evidence_refs,
        claims=claims,
        unresolved=unresolved,
        unexplored=unexplored,
        confidence=confidence,
        recommended_followups=recommended_followups,
    )
