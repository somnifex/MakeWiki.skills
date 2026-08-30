"""ReBattle competitive analysis models and cross-examination logic."""

from __future__ import annotations

import json
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from makewiki_skills.model.claim import ClaimType
from makewiki_skills.model.semantic_model import (
    FAQItem,
    SemanticModel,
    TroubleshootingItem,
    UserTask,
)


class AgentClaim(BaseModel):
    """A structured semantic assertion authored by an LLM scout/debate agent from a
    specific perspective.

    This is the *AgentClaim* layer of the four-layer claim vocabulary: a
    claim an LLM subagent authors about the project (commands, config keys,
    workflows, prerequisites, error cases). It is keyed by
    ``agent_id``/``perspective`` and is the input to ReBattle cross-examination.
    It is *not* a Python-mechanical fact and is *not* yet an accepted,
    adjudicated fact.

    ``semantic_key`` is REQUIRED and is the canonical *meaning* of the claim
    (a dotted path such as ``network.port``). ReBattle groups and compares
    claims by ``semantic_key``, never by a value — two agents asserting
    different values for the same meaning land in one discrepancy, while the
    same value with different meaning never collides.
    """

    claim_id: str = Field(default_factory=lambda: f"claim-{uuid.uuid4().hex[:8]}")
    agent_id: str  # e.g. "agent_red", "agent_blue", "agent_green"
    perspective: str = (
        "user_experience"  # "user_experience" | "code_implementation" | "deployment_ops"
    )
    # Strict ClaimType Literal — pydantic rejects any value outside the
    # vocabulary (e.g. the historical typo "ngx") at model_validate ingress.
    claim_type: ClaimType = "command"
    semantic_key: str  # required — the meaning used for cross-agent grouping
    assertion: str
    value: str | None = None
    subject: str | None = None
    predicate: str | None = None
    object: Any = None
    payload: dict[str, Any] = Field(default_factory=dict)
    source_file: str | None = None
    line_range: tuple[int, int] | None = None
    raw_evidence: str | None = None
    # evidence_refs: source paths underpinning the claim. Populated from
    # source_file when present and not explicitly supplied.
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "inferred"] = "medium"

    @model_validator(mode="after")
    def _map_evidence_refs(self) -> AgentClaim:
        if not self.evidence_refs and self.source_file:
            self.evidence_refs = [self.source_file]
        return self


# Deprecated: use AgentClaim. Kept as a module-level alias so existing
# ``from makewiki_skills.model.rebattle import Claim`` imports keep working.
Claim = AgentClaim


class Challenge(BaseModel):
    """An objection or question raised against a claim during cross-examination."""

    challenge_id: str = Field(default_factory=lambda: f"chg-{uuid.uuid4().hex[:8]}")
    target_claim_id: str
    challenger_agent_id: str
    objection_type: Literal[
        "nonexistent_feature",
        "incorrect_default",
        "missing_prerequisite",
        "unreleased_code",
        "inaccurate_description",
    ] = "inaccurate_description"
    argument: str
    counter_evidence: str | None = None
    severity: Literal["critical", "major", "minor"] = "major"


# Distinguishes a hard, mechanically-proven conflict (two agents asserting
# different structured values for one semantic_key) from an LLM question (same
# structured value, divergent prose). Only a structured_conflict is a hard
# mechanical discrepancy; a semantic_review_candidate is routed to the Judge.
DiscrepancyKind = Literal["structured_conflict", "semantic_review_candidate"]


class Discrepancy(BaseModel):
    """A detected divergence or debate point between different agent perspectives.

    ``kind`` distinguishes hard mechanical conflicts (``structured_conflict``,
    raised by Python when two or more agents disagree on the structured value of
    one ``semantic_key``) from LLM questions (``semantic_review_candidate``,
    same value but divergent prose — not a mechanical discrepancy). Downstream
    can use it to separate hard conflicts from items needing the Judge.
    """

    topic: str
    claim_type: str
    claims: list[AgentClaim] = Field(default_factory=list)
    challenges: list[Challenge] = Field(default_factory=list)
    status: Literal["open", "resolved", "dismissed"] = "open"
    kind: DiscrepancyKind = "structured_conflict"


class AdjudicationResult(BaseModel):
    """The final ruling made by the Judge / Orchestrator on a disputed fact."""

    discrepancy_topic: str
    ruling: Literal["accepted", "rejected", "modified", "hedged"]
    final_assertion: str
    adjudicator_reasoning: str
    verified_via_codebase: bool = False
    source_claim_id: str | None = None


class AdjudicatedClaim(BaseModel):
    """A consensus fact produced by the ReBattle + Judge pipeline.

    This is the *AdjudicatedClaim* layer of the four-layer claim vocabulary:
    an AgentClaim that has survived cross-examination AND received an explicit
    Judge ruling. One is produced per surviving claim ONLY when an explicit
    ``AdjudicationResult`` exists for that claim. A claim with no dispute is
    never wrapped here — "no challenge" means undisputed / pending-adjudication,
    never auto-``accepted``.
    """

    claim: AgentClaim
    ruling: Literal["accepted", "rejected", "modified", "hedged"]
    final_assertion: str
    adjudicator_reasoning: str
    verified_via_codebase: bool = False


class AgentClaimSet(BaseModel):
    """A collection of claims extracted by a single agent."""

    agent_id: str
    perspective: str
    claims: list[AgentClaim] = Field(default_factory=list)

    @classmethod
    def from_agent_bundle(cls, bundle: AgentClaimBundle) -> AgentClaimSet:
        """Build an ``AgentClaimSet`` from a unified :class:`AgentClaimBundle`.

        The bundle carries ``project_name`` plus one agent's claims; this
        projects them onto the ``AgentClaimSet`` shape that ReBattle consumes.
        """
        return cls(
            agent_id=bundle.agent_id,
            perspective=bundle.perspective,
            claims=list(bundle.claims),
        )


class AgentClaimBundle(BaseModel):
    """A unified scout/debate output that can feed BOTH consumer paths.

    The same bundle drives ``verify-claim`` (via ``ClaimSet.from_agent_bundle``,
    see ``model.claim``) and ``rebattle-diff`` (via
    ``AgentClaimSet.from_agent_bundle``), removing the two near-identical JSON
    formats scouts previously maintained. Python adds no semantic content — it
    only projects the bundle onto the shape each consumer needs.
    """

    project_name: str
    agent_id: str
    perspective: str
    claims: list[AgentClaim] = Field(default_factory=list)


# Deprecated: use AgentClaimSet. Kept as a module-level alias so existing
# ``from makewiki_skills.model.rebattle import ClaimSet`` imports keep working.
ClaimSet = AgentClaimSet


class ReBattleResult(BaseModel):
    """Aggregate result of a ReBattle cross-examination session."""

    total_claims: int = 0
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    adjudications: list[AdjudicationResult] = Field(default_factory=list)
    consensus_facts: list[AgentClaim] = Field(default_factory=list)


class ReBattleArena:
    """Detects discrepancies between multiple AgentClaimSets and generates dispute matrices."""

    @staticmethod
    def _structured_value(claim: AgentClaim) -> Any:
        """Extract the canonical STRUCTURED value used for conflict comparison.

        Preference order: ``payload`` when it is a non-empty dict of scalar
        fields (the most structured statement), else ``value``, else ``object``.
        Prose (``assertion``) is deliberately excluded — divergent wording never
        makes a mechanical conflict, and matching wording never hides one.
        """
        payload = claim.payload
        if isinstance(payload, dict) and payload and all(
            isinstance(v, (str, int, float, bool)) or v is None
            for v in payload.values()
        ):
            return payload
        if claim.value is not None:
            return claim.value
        return claim.object

    @staticmethod
    def _canonical_structured(value: Any) -> str:
        """JSON-normalize a structured value so equivalent dicts/key-orders and
        scalar/list forms compare deterministically."""
        try:
            return json.dumps(value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return repr(value)

    @staticmethod
    def detect_discrepancies(claim_sets: list[AgentClaimSet]) -> list[Discrepancy]:
        """Group claims by ``semantic_key`` (meaning) and detect DETERMINISTIC
        conflicts over the normalized STRUCTURED value.

        This never simulates semantic reasoning. Mechanical logic detects only
        what it can prove:

        * Two or more DISTINCT agents sharing a semantics_key but disagreeing on
          the structured value -> ``structured_conflict`` (hard). This is a true
          mechanical discrepancy (e.g. port 3000 vs 8080), regardless of prose.
        * Two or more distinct agents sharing BOTH semantics_key AND the same
          structured value but expressing it with divergent prose ->
          ``semantic_review_candidate`` (an LLM question, NOT a hard
          mechanical discrepancy).
        * A lone claim (no competing agent on the semantic_key) — whatever its
          confidence — is undisputed / pending-adjudication and is routed to
          the LLM Judge. It is NEVER auto-emitted as a discrepancy by Python.
        """
        claims_by_key: dict[str, list[AgentClaim]] = {}

        for cset in claim_sets:
            for claim in cset.claims:
                claims_by_key.setdefault(claim.semantic_key, []).append(claim)

        discrepancies: list[Discrepancy] = []

        for key, matched_claims in claims_by_key.items():
            agents = {c.agent_id for c in matched_claims}
            ctype = matched_claims[0].claim_type

            # A lone claim — or several claims from the SAME agent — is
            # undisputed. It is not a mechanical discrepancy and goes to the
            # Judge; the old confidence-heuristic that flagged it is removed.
            if len(agents) < 2:
                continue

            # Group by normalized structured value; compare across agents.
            value_groups: dict[str, list[AgentClaim]] = {}
            for claim in matched_claims:
                norm = ReBattleArena._canonical_structured(
                    ReBattleArena._structured_value(claim)
                )
                value_groups.setdefault(norm, []).append(claim)

            if len(value_groups) > 1:
                # Distinct structured values across agents -> hard conflict.
                discrepancies.append(
                    Discrepancy(
                        topic=key,
                        claim_type=ctype,
                        claims=matched_claims,
                        status="open",
                        kind="structured_conflict",
                    )
                )
            else:
                # All agents agree on the structured value; the only possible
                # difference is prose -> an LLM question, not a hard conflict.
                assertions = {c.assertion.strip() for c in matched_claims}
                if len(assertions) > 1:
                    discrepancies.append(
                        Discrepancy(
                            topic=key,
                            claim_type=ctype,
                            claims=matched_claims,
                            status="open",
                            kind="semantic_review_candidate",
                        )
                    )

        return discrepancies

    @staticmethod
    def synthesize_consensus(
        claim_sets: list[AgentClaimSet],
        adjudications: list[AdjudicationResult] | None = None,
    ) -> list[AgentClaim | AdjudicatedClaim]:
        """Synthesize consensus by ``semantic_key``, only wrapping explicitly
        adjudicated claims.

        A claim with an explicit ``AdjudicationResult`` becomes an
        ``AdjudicatedClaim`` carrying that ruling. A claim with NO adjudication
        is returned as a plain, pending ``AgentClaim`` (undisputed /
        pending-adjudication) — it is NEVER auto-accepted. "No challenge" never
        fabricates ``ruling="accepted"``; only a Judge ruling does.
        """
        if not adjudications:
            return _consensus_agent_claims(claim_sets)

        # Adjudicated path: build semantic_key -> ruling lookup and produce one
        # AdjudicatedClaim per claim that carries an explicit ruling.
        ruling_by_key: dict[str, AdjudicationResult] = {}
        for ruling in adjudications:
            ruling_by_key[ruling.discrepancy_topic.lower()] = ruling

        seen: set[str] = set()
        consensus: list[AgentClaim | AdjudicatedClaim] = []

        for cset in claim_sets:
            for claim in cset.claims:
                key = claim.semantic_key.lower()
                adj = ruling_by_key.get(key)

                # A claim whose semantic_key was explicitly rejected is dropped.
                if adj is not None and adj.ruling == "rejected":
                    continue

                if key in seen:
                    continue
                seen.add(key)

                if adj is not None:
                    consensus.append(
                        AdjudicatedClaim(
                            claim=claim,
                            ruling=adj.ruling,
                            final_assertion=adj.final_assertion,
                            adjudicator_reasoning=adj.adjudicator_reasoning,
                            verified_via_codebase=adj.verified_via_codebase,
                        )
                    )
                else:
                    # No explicit adjudication -> leave as pending AgentClaim,
                    # never auto-accepted.
                    consensus.append(claim)

        return consensus


def _consensus_agent_claims(
    claim_sets: list[AgentClaimSet],
    _adjudications: list[AdjudicationResult] | None = None,
) -> list[AgentClaim | AdjudicatedClaim]:
    """Surviving (unadjudicated) AgentClaims deduplicated by ``semantic_key``.

    Returned as the consensus union type so ``synthesize_consensus`` can hand
    them back unchanged alongside real ``AdjudicatedClaim`` results. The
    underlying values are always plain pending ``AgentClaim`` objects — no
    ``AdjudicatedClaim`` is fabricated here. Without an adjudication list there
    are no rejected topics, so no filtering happens.
    """
    seen: set[str] = set()
    consensus: list[AgentClaim | AdjudicatedClaim] = []
    for cset in claim_sets:
        for claim in cset.claims:
            if claim.semantic_key in seen:
                continue
            seen.add(claim.semantic_key)
            consensus.append(claim)
    return consensus


def fold_adjudicated_into_semantic_model(
    adjudicated: list[AdjudicatedClaim],
    model: SemanticModel,
) -> SemanticModel:
    """Mechanical bridge: fold accepted AdjudicatedClaims into the SemanticModel.

    This is the ONLY Python path by which cognitive content enters the
    authoritative SemanticModel, and it ingests ONLY ``AdjudicatedClaim`` (the
    Judge's ruling) — never raw ``AgentClaim`` / ``MechanicalAssertion``. Python
    does not invent cognitive fields; without a Judge ruling they stay empty /
    ``unknown``. Rejected and hedged rulings are never folded in; accepted and
    modified rulings (both authoritative) are. The same ``model`` is returned
    (mutated in place).
    """
    for adj in adjudicated:
        if adj.ruling not in ("accepted", "modified"):
            continue
        ctype = adj.claim.claim_type
        text = adj.final_assertion or adj.claim.assertion
        if ctype == "faq_topic":
            model.faq.append(FAQItem(question=adj.claim.semantic_key, answer=text))
            model.provenance.faq = "llm"
        elif ctype == "troubleshooting":
            model.troubleshooting.append(
                TroubleshootingItem(symptom=adj.claim.semantic_key, solution=text)
            )
            model.provenance.troubleshooting = "llm"
        elif ctype == "workflow":
            model.user_tasks.append(
                UserTask(title=adj.claim.semantic_key, steps=[text] if text else [])
            )
            model.provenance.user_tasks = "llm"
        else:
            # Mechanical or unmapped cognitive types are not invented here; they
            # are sourced from evidence or rendered by the Skill layer.
            continue
    return model
