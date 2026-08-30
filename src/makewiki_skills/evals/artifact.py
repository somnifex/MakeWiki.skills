"""Stable run-artifact contract for MakeWiki evals.

Every ``/makewiki`` eval run produces a bundle of structured JSON files under
``<runs>/<trap>/run-<n>/``. This module is the single source of truth for that
contract: the pydantic models below validate any bundle a host writes, and the
fake-LLM fixture driver emits the identical shape deterministically.

The contract mirrors the authoritative handoffs (Scout -> ReBattle -> Judge ->
SemanticModel -> Writer -> mechanical L0-L5 -> Auditor -> Quality Gate), so a
reviewer can inspect *every* handoff that produced the final docs. Files are
scoring-neutral: they record what each agent *did* (claims, rulings,
verdicts), never a judgment about whether the prose reads well.

A run bundle lives in a directory and is indexed by ``run.json``::

    run/
    ├── run.json                 # trap, run_id, seed, timestamps, host notes
    ├── evidence.json            # mechanical evidence (claim IDs, facts)
    ├── agent_claims.json        # scout AgentClaimSet per perspective
    ├── rebattle.json            # ReBattle discrepancies (topics = semantic keys)
    ├── adjudications.json       # Judge rulings per discrepancy
    ├── semantic_model.json      # folded SemanticModel (user_tasks, config, ...)
    ├── semantic_audit.json      # Auditor SemanticAuditBundle (item-level)
    ├── mechanical_report.json   # L0-L5 VerificationReport (layer verdicts)
    ├── quality_gate.json        # four-state verdict + ci_exit_code
    └── docs/                    # writer output markdown, one file per language
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Bump when a field is added/renamed/removed so hosts re-validate old bundles.
SCHEMA_VERSION = "1.0.0"

RUN_INDEX_FILE = "run.json"
ARTIFACT_FILES = (
    "run.json",
    "evidence.json",
    "agent_claims.json",
    "rebattle.json",
    "adjudications.json",
    "semantic_model.json",
    "semantic_audit.json",
    "mechanical_report.json",
    "quality_gate.json",
)
DOCS_DIR = "docs"


# ---------------------------------------------------------------------------
# Individual artifacts
# ---------------------------------------------------------------------------


class RunMeta(BaseModel):
    """Identity + provenance of one eval run."""

    schema_version: str = SCHEMA_VERSION
    trap: str
    run_id: str
    seed: int = 0
    host: str = ""  # e.g. "claude-sonnet-5", or "fixture" for a fake-LLM run
    executed_by: str = "fixture"  # "host" or "fixture"
    timestamp: str = ""  # ISO-8601, when provided


class EvidenceArtifact(BaseModel):
    """Mechanical evidence collected over the trap repo."""

    # One entry per mechanically-provable fact/claim. ``id`` is stable and
    # matches a gold ``verified_facts`` id when the fact is a gold fact.
    facts: list[dict[str, Any]] = Field(default_factory=list)
    detected_packages: list[str] = Field(default_factory=list)


class AgentClaimArtifact(BaseModel):
    agent_id: str
    perspective: str
    # Each claim recorded with its stable fields only (id / semantic_key /
    # claim_type / assertion / value / confidence). No free-form prose scoring.
    claims: list[dict[str, Any]] = Field(default_factory=list)


class AgentClaimsArtifact(BaseModel):
    """Scout-stage agent claim bundles, one per perspective."""

    sets: list[AgentClaimArtifact] = Field(default_factory=list)


class DiscrepancyArtifact(BaseModel):
    """One ReBattle discrepancy. ``topic`` IS the semantic key that was in
    dispute, so an evaluator can mechanically check that the right conflict
    was surfaced."""

    topic: str
    participants: list[str] = Field(default_factory=list)
    source_values: dict[str, str] = Field(default_factory=dict)


class RebattleArtifact(BaseModel):
    discrepancies: list[DiscrepancyArtifact] = Field(default_factory=list)


class AdjudicationArtifact(BaseModel):
    """One Judge ruling. ``topic`` matches the discrepancy topic (semantic key);
    ``final_assertion`` is the value the Judge accepted; ``verified_via_codebase``
    records whether the ruling was grounded in mechanical code evidence."""

    topic: str
    ruling: str = "accepted"  # accepted | rejected | hedged
    final_assertion: str | None = None
    verified_via_codebase: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    adjudicator_reasoning: str = ""


class AdjudicationsArtifact(BaseModel):
    rulings: list[AdjudicationArtifact] = Field(default_factory=list)


class SemanticModelArtifact(BaseModel):
    """The folded authoritative SemanticModel, reduced to the structured
    surfaces the evaluator can check (config keys, user_tasks, provenances)."""

    dotenv: list[str] = Field(default_factory=list)
    user_tasks: list[str] = Field(default_factory=list)
    troubleshooting: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)
    claims: list[dict[str, Any]] = Field(default_factory=list)


class AuditVerdictArtifact(BaseModel):
    """One item-level Auditor verdict, keyed by its stable review_item_id."""

    review_item_id: str
    layer: str
    status: str  # passed | failed | ...
    auditor: str = ""
    evidence_refs: list[str] = Field(default_factory=list)


class SemanticAuditArtifact(BaseModel):
    auditor: str = ""
    documents_digest: str = ""
    verdicts: list[AuditVerdictArtifact] = Field(default_factory=list)
    # Honest completeness: whether the bundle is document-fresh and (per the
    # merge) how many expected items it adjudicated.
    rejected: bool = False
    rejection_reason: str = ""


class CheckArtifact(BaseModel):
    layer: str
    target: str = ""
    claim_type: str = ""
    claim_text: str = ""
    status: str = "pending"
    review_item_id: str | None = None
    detail: str = ""


class LayerArtifact(BaseModel):
    layer: str
    name: str = ""
    verdict: str = "pending"  # passed | failed | pending | not_applicable
    checks: list[CheckArtifact] = Field(default_factory=list)


class MechanicalReportArtifact(BaseModel):
    """The L0-L5 VerificationReport, flattened for stable mechanical scoring."""

    layers: list[LayerArtifact] = Field(default_factory=list)
    total_checks: int = 0


class QualityGateArtifact(BaseModel):
    """The honest four-state verdict, separated from the CI exit code.

    ``verdict`` is the truth verdict (passed / pending_semantic_review /
    pending_mechanical_verification / failed); ``ci_exit_code`` is the exit
    policy (0 / 1 / 0-or-2 / 3). They must never be conflated.
    """

    verdict: str = "pending_mechanical_verification"
    ci_exit_code: int = 0
    semantic_complete: bool = False
    pending_llm_layers: list[str] = Field(default_factory=list)
    mechanical_passed: bool = False


# ---------------------------------------------------------------------------
# Run bundle assembly / loading
# ---------------------------------------------------------------------------


def run_artifact_map() -> dict[str, type[BaseModel]]:
    """name -> model, for the top-level files (run.json handled separately)."""
    return {
        "evidence.json": EvidenceArtifact,
        "agent_claims.json": AgentClaimsArtifact,
        "rebattle.json": RebattleArtifact,
        "adjudications.json": AdjudicationsArtifact,
        "semantic_model.json": SemanticModelArtifact,
        "semantic_audit.json": SemanticAuditArtifact,
        "mechanical_report.json": MechanicalReportArtifact,
        "quality_gate.json": QualityGateArtifact,
    }


def save_run(run_dir: Path, meta: RunMeta, artifacts: dict[str, BaseModel]) -> None:
    """Write ``meta`` as run.json and each artifact to its named file."""
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / RUN_INDEX_FILE).write_text(
        json.dumps(meta.model_dump(), indent=2), encoding="utf-8"
    )
    for filename, model in artifacts.items():
        if filename == RUN_INDEX_FILE:
            continue
        (run_dir / filename).write_text(
            json.dumps(model.model_dump(), indent=2), encoding="utf-8"
        )


def load_run(run_dir: Path) -> tuple[RunMeta, dict[str, BaseModel]]:
    """Load and validate a run bundle. Raises on a malformed/incomplete bundle."""
    run_dir = Path(run_dir)
    meta = RunMeta.model_validate_json(
        (run_dir / RUN_INDEX_FILE).read_text(encoding="utf-8")
    )
    if meta.schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"run schema {meta.schema_version!r} != supported {SCHEMA_VERSION!r}"
        )
    artifacts: dict[str, BaseModel] = {}
    for filename, model in run_artifact_map().items():
        path = run_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"run bundle missing {filename} in {run_dir}")
        artifacts[filename] = model.model_validate_json(path.read_text(encoding="utf-8"))
    return meta, artifacts


def docs_dir_for(run_dir: Path) -> Path:
    return run_dir / DOCS_DIR
