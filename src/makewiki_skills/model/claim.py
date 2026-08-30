"""Structured Claim data models and builders for evidence-backed documentation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast, get_args

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from makewiki_skills.model.rebattle import AgentClaimBundle

from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult

Confidence = Literal["high", "medium", "low", "inferred"]

# The full ClaimType vocabulary covering BOTH the mechanical types Python can
# prove deterministically (command/config/path/version) AND the cognitive types
# only an LLM Agent may author (workflow/persona/prerequisite/behavior/
# error_case/faq_topic/troubleshooting/constraint/capability/architecture).
# There is no "ngx" type; that was a historical typo.
ClaimType = Literal[
    "command",
    "config",
    "path",
    "version",
    "workflow",
    "persona",
    "prerequisite",
    "behavior",
    "error_case",
    "faq_topic",
    "troubleshooting",
    "constraint",
    "capability",
    "architecture",
]

# Machine-checkable membership set mirroring the ClaimType vocabulary.
CLAIM_TYPES: frozenset[str] = frozenset(get_args(ClaimType))

VerificationStatus = Literal[
    "pending",
    "passed",
    "failed",
    "unknown",
    "not_applicable",
]


class ClaimEvidence(BaseModel):
    """Pointer to specific project source that supports a claim."""

    source_file: str
    line_start: int | None = None
    line_end: int | None = None
    raw_text: str | None = None
    extraction_method: str = "direct_read"
    confidence: Confidence = "medium"


class VerificationState(BaseModel):
    """Multi-layer grounding verification results for a claim (L0 - L5)."""

    l0_syntax: VerificationStatus = "pending"
    l1_existence: VerificationStatus = "pending"
    l2_interface: VerificationStatus = "pending"
    l3_behavior: VerificationStatus = "pending"
    l4_cross_language: VerificationStatus = "pending"
    l5_epistemic: VerificationStatus = "pending"


class Claim(BaseModel):
    """A structured, verifiable proposition about project capabilities.

    In the four-layer claim vocabulary this model serves two layers
    depending on ``provenance``:

    * ``provenance == "python_fact"`` — the **MechanicalAssertion** layer: a
      Python-normalized, deterministic statement of evidence (e.g. built by
      :func:`build_claims_from_evidence`).
    * ``provenance == "llm_claim"`` — the **AgentClaim** layer: a semantic
      claim authored by an LLM scout/debate agent (ingressed via
      :meth:`ClaimSet.from_llm_json`).
    * ``provenance == "adjudicated"`` — an accepted post-ReBattle consensus
      fact (an AgentClaim that survived cross-examination and carries the
      Judge's ruling once folded into the model).

    Keep ``Claim``/``ClaimSet`` as the canonical class names here — the
    pipeline and CLI depend on them.
    """

    claim_id: str
    # claim_type covers the full ClaimType vocabulary: mechanical types Python
    # proves (command | config | path | version) and cognitive types only an LLM
    # Agent authors (workflow | persona | prerequisite | behavior | error_case |
    # faq_topic | troubleshooting | constraint | capability | architecture).
    # It is a strict Literal, so pydantic rejects any value outside the
    # vocabulary (e.g. the historical typo "ngx") at model_validate / ingress.
    claim_type: ClaimType
    semantic_key: str

    subject: str
    predicate: str
    object: Any

    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[ClaimEvidence] = Field(default_factory=list)
    confidence: Confidence = "medium"
    verification: VerificationState = Field(default_factory=VerificationState)
    uncertainty: str | None = None
    # Provenance distinguishes deterministic facts extracted by Python from
    # semantic claims authored by LLM subagents. Python never invents the
    # latter; it validates and verifies them.
    provenance: Literal["python_fact", "llm_claim", "adjudicated"] = "python_fact"


# MechanicalAssertion is the Python-normalized, deterministic statement of
# evidence produced by the scanner/builders (provenance == "python_fact").
# It is a type alias over Claim so downstream consumers can name the layer
# explicitly without creating a second, unrelated class. Not to be confused
# with AgentClaim (LLM-authored) or AdjudicatedClaim (post-ReBattle ruling).
MechanicalAssertion = Claim


class ClaimSet(BaseModel):
    """A collection of structured claims for a project."""

    project_name: str
    claims: list[Claim] = Field(default_factory=list)

    def by_type(self, claim_type: str) -> list[Claim]:
        return [c for c in self.claims if c.claim_type == claim_type]

    def get_by_id(self, claim_id: str) -> Claim | None:
        return next((c for c in self.claims if c.claim_id == claim_id), None)

    @classmethod
    def from_llm_json(cls, project_name: str, data: list[dict[str, Any]] | dict[str, Any]) -> ClaimSet:
        """Build a ClaimSet from LLM-authored claim JSON.

        This is the **AgentClaim** ingress: the Skill layer's Claim step emits
        semantic claims (workflows, personas, FAQ topics, troubleshooting root
        causes) as JSON. Python validates their schema and marks
        ``provenance="llm_claim"`` so downstream verifiers know these require
        LLM judgment rather than mechanical proof.
        """
        raw = data.get("claims", data) if isinstance(data, dict) else data
        if not isinstance(raw, list):
            raise ValueError("LLM claim payload must be a list of claim objects (or {'claims': [...]})")

        claims: list[Claim] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            claim = Claim.model_validate(item)
            claim.provenance = "llm_claim"
            claims.append(claim)
        return cls(project_name=project_name, claims=claims)

    @classmethod
    def from_agent_bundle(cls, bundle: AgentClaimBundle) -> ClaimSet:
        """Convert an :class:`AgentClaimBundle` into a :class:`ClaimSet`.

        This lets ONE scout/debate bundle feed both ``verify-claim`` (via
        ``ClaimSet``) and ``rebattle-diff`` (via ``AgentClaimSet``) without
        maintaining two divergent JSON formats. Each ``AgentClaim`` becomes a
        ``Claim`` marked ``provenance="llm_claim"``. Field names are shared
        between the two models, so the conversion is a mechanical 1:1 mapping —
        Python invents no semantic content here.
        """
        claims: list[Claim] = []
        for ac in bundle.claims:
            claim = Claim(
                claim_id=ac.claim_id,
                claim_type=ac.claim_type,
                semantic_key=ac.semantic_key,
                subject=ac.subject or ac.semantic_key,
                predicate=ac.predicate or "asserts",
                object=ac.object if ac.object is not None else ac.value,
                payload=dict(ac.payload),
                confidence=ac.confidence,
            )
            claim.provenance = "llm_claim"
            claims.append(claim)
        return cls(project_name=bundle.project_name, claims=claims)


def _slugify(text: str) -> str:
    """Create a URL/ID friendly slug from arbitrary text."""
    clean = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")
    return clean.lower() or "item"


def build_claims_from_evidence(
    detection: ProjectDetectionResult,
    registry: EvidenceRegistry,
) -> ClaimSet:
    """Transform collected EvidenceFacts into structured Claim models (4 initial types)."""
    claims: list[Claim] = []
    seen_keys: set[tuple[str, str]] = set()

    for fact in registry.all_facts():
        val = (fact.value or fact.claim).strip()
        if not val:
            continue

        claim_evidence = [
            ClaimEvidence(
                source_file=link.source_path,
                line_start=link.line_range[0] if link.line_range else None,
                line_end=link.line_range[1] if link.line_range else None,
                raw_text=link.raw_text,
                extraction_method=link.extraction_method,
                confidence=link.confidence if link.confidence in ("high", "medium", "low", "inferred") else "medium",
            )
            for link in fact.evidence
        ]

        conf: Confidence = (
            cast(Confidence, fact.best_confidence)
            if fact.best_confidence in ("high", "medium", "low", "inferred")
            else "medium"
        )

        if fact.fact_type == "command":
            slug = _slugify(val)
            key = ("command", slug)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            cid = f"CMD_{slug.upper()}"[:40]
            parts = val.split()
            exe = parts[0] if parts else detection.project_name
            args = parts[1:] if len(parts) > 1 else []

            claims.append(
                Claim(
                    claim_id=cid,
                    claim_type="command",
                    semantic_key=f"cli.command.{slug}",
                    subject=detection.project_name,
                    predicate="supports_command",
                    object=val,
                    payload={
                        "command": val,
                        "executable": exe,
                        "arguments": args,
                    },
                    evidence=claim_evidence,
                    confidence=conf,
                )
            )

        elif fact.fact_type == "config_key":
            slug = _slugify(val)
            key = ("config", slug)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            cid = f"CFG_{slug.upper()}"[:40]
            claims.append(
                Claim(
                    claim_id=cid,
                    claim_type="config",
                    semantic_key=f"config.parameter.{slug}",
                    subject=val,
                    predicate="is_configuration_option",
                    object=val,
                    payload={"key": val},
                    evidence=claim_evidence,
                    confidence=conf,
                )
            )

        elif fact.fact_type == "path":
            slug = _slugify(val)
            key = ("path", slug)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            cid = f"PATH_{slug.upper()}"[:40]
            claims.append(
                Claim(
                    claim_id=cid,
                    claim_type="path",
                    semantic_key=f"filesystem.path.{slug}",
                    subject=val,
                    predicate="exists_in_repository",
                    object=val,
                    payload={"path": val},
                    evidence=claim_evidence,
                    confidence=conf,
                )
            )

        elif fact.fact_type == "version":
            key = ("version", val)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            cid = f"VER_{_slugify(detection.project_name).upper()}"[:40]
            claims.append(
                Claim(
                    claim_id=cid,
                    claim_type="version",
                    semantic_key="project.version",
                    subject=detection.project_name,
                    predicate="has_version",
                    object=val,
                    payload={"version": val},
                    evidence=claim_evidence,
                    confidence=conf,
                )
            )

    return ClaimSet(
        project_name=detection.project_name,
        claims=claims,
    )


def verify_claims_against_codebase(
    claim_set: ClaimSet,
    target_dir: Path,
) -> ClaimSet:
    """Verify claims against project filesystem and mark verification states."""
    target_dir = Path(target_dir).resolve()

    # claim_type must be a member of the full, unambiguous ClaimType vocabulary
    # (no "ngx"). Claim ids are validated only as stable unique slugs — they are
    # NOT forced to carry a mechanical CMD_/CFG_/PATH_/VER_ prefix, because
    # cognitive claims (workflow, persona, faq_topic, ...) use free-form ids such
    # as "FW_AUTH_FLOW".
    claim_id_slug = re.compile(r"^[A-Za-z0-9._-]+$")
    # A semantic key is a slash-shaped dotted path, e.g. "cli.command.scan" or
    # "config.parameter.foo" — at least one dot-separated component.
    semantic_key_pattern = re.compile(r"^[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+$")

    for claim in claim_set.claims:
        # L0 Syntax check: genuine well-formedness, not mere field non-emptiness.
        # A claim passes only when the verifier actually validated its structure;
        # anything malformed is "failed", anything uncheckable is "pending".
        l0_ok = (
            isinstance(claim.claim_id, str)
            and bool(claim_id_slug.match(claim.claim_id.strip()))
            and claim.claim_type in CLAIM_TYPES
            and isinstance(claim.semantic_key, str)
            and bool(semantic_key_pattern.match(claim.semantic_key.strip()))
            and isinstance(claim.subject, str)
            and bool(claim.subject.strip())
        )
        if l0_ok:
            claim.verification.l0_syntax = "passed"
        elif (
            not isinstance(claim.claim_id, str)
            or not isinstance(claim.semantic_key, str)
            or not isinstance(claim.subject, str)
        ):
            # Missing/unknown fields mean we cannot even assess well-formedness.
            claim.verification.l0_syntax = "pending"
        else:
            claim.verification.l0_syntax = "failed"

        # L1 Existence check
        if claim.claim_type == "path":
            p = claim.object
            if isinstance(p, str):
                norm = p.lstrip("./")
                if (target_dir / norm).exists():
                    claim.verification.l1_existence = "passed"
                else:
                    claim.verification.l1_existence = "failed"
            else:
                # Path object of unexpected type: no existence check was executed.
                claim.verification.l1_existence = "pending"
        elif claim.claim_type == "command":
            # Only pass when there is genuine high/medium evidence that proves
            # existence, or when the L1 verifier resolves the command against a
            # known command table. A command claim with no such proof is never
            # passed here - it is reported pending (not yet proven).
            if any(e.confidence in ("high", "medium") for e in claim.evidence):
                claim.verification.l1_existence = "passed"
            else:
                claim.verification.l1_existence = "pending"
        elif claim.claim_type in ("config", "version"):
            claim.verification.l1_existence = "passed" if claim.evidence else "failed"
        else:
            # Unhandled claim type: no L1 check was executed.
            claim.verification.l1_existence = "pending"

        # L2 Interface check — delegated to the real L2InterfaceVerifier, which
        # runs in the VerificationOrchestrator. Here we only note that a
        # mechanical interface proof is possible for evidence-backed facts; it is
        # never blindly marked "passed".
        if claim.provenance == "python_fact" and claim.evidence and claim.claim_type in (
            "command",
            "config",
            "path",
        ):
            claim.verification.l2_interface = "pending"
        else:
            # LLM-authored semantic claims require LLM judgment, not mechanical proof.
            claim.verification.l2_interface = "pending"

        # L3 Behavior check — behavioral proof is LLM-judged (the Skill's Auditor
        # reasons over evidence). Python never asserts behavior it cannot prove.
        claim.verification.l3_behavior = "pending"

        # L4 Cross-language
        claim.verification.l4_cross_language = "pending"

        # L5 Epistemic check — LLM-judged. Python never asserts epistemic
        # soundness, so L5 is always left "pending" for the Skill's Auditor to
        # reason over. Low/inferred confidence additionally records the reason.
        if claim.confidence == "inferred" or claim.confidence == "low":
            claim.uncertainty = "Inferred from configuration or heuristic scan"
        claim.verification.l5_epistemic = "pending"

    return claim_set
