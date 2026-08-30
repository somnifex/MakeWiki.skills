"""Quality Gate: single gate over all L0-L5 verification layers.

The Quality Gate aggregates the per-layer reports produced by
``VerificationOrchestrator`` into one decision — PASS / FAIL / PENDING_SEMANTIC_REVIEW
— that the CLI maps to a CI exit code and the Skill layer consults before shipping
a document set.

Python verifies what can be mechanically proven (L0/L1/L2 + L4a mechanical parity).
L3 behavior, L4b prose-parity and L5 epistemic review are LLM-judged; when any of
them is still ``pending`` the gate reports ``verdict="pending_semantic_review"``
and ``semantic_complete=False`` so the pending state is never hidden. When a
mechanical layer fails the gate is ``failed`` (exit code 1). The legacy ``passed``
bool and ``exit_code`` preserve the historical allow-pending-True behaviour (a
mechanical pass with pending LLM layers yields ``passed=True`` / exit 0), while
``verdict`` lets a human always see the true pending state.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig, RevisionConfig
from makewiki_skills.verification.report import (
    ComprehensiveVerificationReport,
    VerificationCheck,
)

# Mechanical pass + pending LLM layers => pending_semantic_review (honest label);
# mechanical pass + all LLM layers adjudicated + no blocking => passed; any
# L0/L1/L2 (or L4a) mechanical failure => failed.
QualityGateVerdict = Literal["passed", "pending_semantic_review", "failed"]


class QualityGateResult(BaseModel):
    """Aggregated head-of-line decision from running all verification layers."""

    passed: bool
    syntax_passed: bool
    existence_passed: bool
    interface_passed: bool
    behavior_passed: bool
    cross_language_passed: bool
    epistemic_passed: bool
    grounding_score: float
    unresolved_critical: int = 0
    unresolved_major: int = 0
    unresolved_minor: int = 0
    revision_rounds: int = 0
    details: dict[str, object] = Field(default_factory=dict)

    # --- Honesty model (backward-compatible additions) -----------------------
    verdict: QualityGateVerdict = "pending_semantic_review"
    mechanical_passed: bool = False
    semantic_complete: bool = False
    mechanical_score: float = 0.0
    semantic_score: float | None = None
    l0_status: str = "pending"
    l1_status: str = "pending"
    l2_status: str = "pending"
    l3_status: str = "pending"
    l4_status: str = "pending"
    l5_status: str = "pending"
    pending_llm_layers: list[str] = Field(default_factory=list)

    @property
    def exit_code(self) -> int:
        """CI exit code: 0 unless the verdict is ``failed``.

        Pending-semantic-review is not a mechanical failure, so it exits 0
        (consistent with the historical allow-pending-True contract). Only an
        outright mechanical failure exits 1.
        """
        return 1 if self.verdict == "failed" else 0


def _layer_status(
    report: ComprehensiveVerificationReport, layer: str
) -> Literal["passed", "failed", "pending", "not_applicable"]:
    layer_report = report.layers.get(layer)
    if layer_report is None:
        return "pending"
    return layer_report.verdict


def _l4a_mechanical_checks(
    report: ComprehensiveVerificationReport,
) -> list[VerificationCheck]:
    """The L4 checks that are mechanically decidable (stable-block + fact parity)."""
    l4 = report.layers.get("L4")
    if l4 is None:
        return []
    return [c for c in l4.checks if c.claim_type == "l4a_mechanical"]


def _score(passed: int, total: int) -> float:
    return round(passed / total, 3) if total else 1.0


def evaluate_quality_gate(
    report: ComprehensiveVerificationReport,
    revision: RevisionConfig | MakeWikiConfig | None = None,
    *,
    fail_on_critical: bool = True,
    min_grounding_score: float | None = None,
    resolved_critical_in_rounds: int = 0,
    allow_pending_llm_layers: bool | None = None,
) -> QualityGateResult:
    """Evaluate a comprehensive report against configurable quality thresholds.

    Parameters
    ----------
    report:
        The aggregate L0-L5 report from the orchestrator.
    revision:
        Either a ``RevisionConfig`` (or a full ``MakeWikiConfig`` whose
        ``revision`` is read) supplying ``min_grounding_score``.
    fail_on_critical:
        Whether any failed mechanical layer or unresolved critical item fails the
        gate. LLM-judged layers left ``pending`` are reported but do not by
        themselves fail the gate unless their checks explicitly failed.
    allow_pending_llm_layers:
        If provided, overrides the auto-detection from the config; when True,
        unresolved LLM-judged layers (L3 / L4-prose / L5) that are pending do
        not by themselves fail the gate.
    """
    min_score = min_grounding_score
    if min_score is None:
        if isinstance(revision, MakeWikiConfig):
            min_score = revision.revision.min_grounding_score
        elif revision is not None:
            min_score = revision.min_grounding_score
        else:
            min_score = 1.0

    pending_allowed = allow_pending_llm_layers
    if pending_allowed is None and isinstance(revision, MakeWikiConfig):
        pending_allowed = revision.quality.allow_pending_llm_layers
    if pending_allowed is None:
        pending_allowed = True

    # ---- per-layer honest status --------------------------------------------
    l0_status = _layer_status(report, "L0")
    l1_status = _layer_status(report, "L1")
    l2_status = _layer_status(report, "L2")
    l3_status = _layer_status(report, "L3")
    l4_status = _layer_status(report, "L4")
    l5_status = _layer_status(report, "L5")

    syntax_passed = l0_status == "passed"
    existence_passed = l1_status == "passed"
    interface_passed = l2_status == "passed"
    behavior_passed = l3_status == "passed"
    cross_language_passed = l4_status == "passed"
    epistemic_passed = l5_status == "passed"

    # ---- mechanical score (L0/L1/L2 + L4a) — independent of pending LLM ------
    mechanical_total = 0
    mechanical_passed_count = 0
    for name in ("L0", "L1", "L2"):
        lr = report.layers.get(name)
        if lr is not None:
            mechanical_total += lr.total_checks
            mechanical_passed_count += lr.passed_count
    l4a_checks = _l4a_mechanical_checks(report)
    l4a_total = len(l4a_checks)
    l4a_passed = sum(1 for c in l4a_checks if c.verified)
    mechanical_total += l4a_total
    mechanical_passed_count += l4a_passed
    mechanical_score = _score(mechanical_passed_count, mechanical_total)

    # Backward-compat aggregation over every layer (includes pending LLM layers,
    # which is why it can sit below the mechanical score).
    grounding_score = _score(report.passed_count, report.total_checks)

    # ---- semantic (LLM) state -----------------------------------------------
    llm_statuses = {
        "L3": l3_status,
        "L4": l4_status,
        "L5": l5_status,
    }
    pending_llm_layers = [
        name for name, st in llm_statuses.items() if st in ("pending", "unknown")
    ]
    semantic_complete = not bool(pending_llm_layers)

    if pending_llm_layers:
        semantic_score: float | None = None
    else:
        sem_total = 0
        sem_passed = 0
        for name in ("L3", "L4", "L5"):
            lr = report.layers.get(name)
            if lr is not None:
                sem_total += lr.total_checks
                sem_passed += lr.passed_count
        semantic_score = _score(sem_passed, sem_total)

    # ---- unresolved counts (severity-differentiated) -------------------------
    mechanical_failed_count = sum(
        report.layers[n].failed_count
        for n in ("L0", "L1", "L2")
        if n in report.layers
    ) + sum(1 for c in l4a_checks if c.status == "failed")
    llm_failed = sum(
        report.layers[n].failed_count
        for n in ("L3", "L4", "L5")
        if n in report.layers
    )
    warning_count = sum(lr.warning_count for lr in report.layers.values())

    meets_score = mechanical_score >= min_score
    unresolved_critical = (
        mechanical_failed_count + (0 if mechanical_score >= min_score else 1)
    )
    unresolved_major = llm_failed
    unresolved_minor = warning_count

    # ---- mechanical decision ------------------------------------------------
    all_mechanical = syntax_passed and existence_passed and interface_passed
    any_l4a_failed = any(c.status == "failed" for c in l4a_checks)
    any_mechanical_failed = (
        l0_status == "failed"
        or l1_status == "failed"
        or l2_status == "failed"
        or any_l4a_failed
    )
    # Mechanical layers that are still pending (e.g. an empty L1/L2 whose checks
    # were never populated → "pending") but did not fail. Existence/interface are
    # thus not yet proven; the gate must not report a clean PASS over them.
    mechanical_pending = (not all_mechanical) and not any_mechanical_failed

    # ---- verdict (honest) ----------------------------------------------------
    # A mechanical-layer failure OR a mechanical-score shortfall drives "failed";
    # so does an EXPLICIT LLM-judged layer failure (a documented check that
    # contradicted or was never proven cannot be papered over — the docstring
    # promises "unless their checks explicitly failed"). Otherwise pending LLM
    # layers hold the gate at "pending_semantic_review"; un-proven (pending)
    # mechanical layers also withhold "passed" and report pending; only a fully
    # adjudicated, non-blocking report is "passed".
    if any_mechanical_failed or not meets_score:
        verdict: QualityGateVerdict = "failed"
    elif llm_failed:
        verdict = "failed"
    elif mechanical_pending:
        verdict = "pending_semantic_review"
    elif pending_llm_layers:
        verdict = "pending_semantic_review"
    else:
        verdict = "passed"

    # ---- backward-compat ``passed`` ----------------------------------------
    # Keeps the historical allow-pending-True contract: a mechanical pass with
    # pending LLM layers still yields passed=True (and exit 0). A mechanical
    # failure OR an explicitly-failed LLM-judged check always yields passed=False
    # (an explicit failure is a stronger signal than "pending" and is never
    # tolerated by the allow-pending knob — that knob governs *pending* only).
    if fail_on_critical:
        passed = bool(
            all_mechanical and meets_score and not any_l4a_failed and llm_failed == 0
        )
    else:
        # Informational mode: still fail on outright provable gaps, and an
        # explicitly-failed LLM check is a demonstrated failure, not a gap.
        passed = bool(meets_score and existence_passed and llm_failed == 0)

    return QualityGateResult(
        passed=passed,
        verdict=verdict,
        syntax_passed=syntax_passed,
        existence_passed=existence_passed,
        interface_passed=interface_passed,
        behavior_passed=behavior_passed,
        cross_language_passed=cross_language_passed,
        epistemic_passed=epistemic_passed,
        mechanical_passed=all_mechanical and not any_l4a_failed,
        semantic_complete=semantic_complete,
        grounding_score=grounding_score,
        mechanical_score=mechanical_score,
        semantic_score=semantic_score,
        l0_status=l0_status,
        l1_status=l1_status,
        l2_status=l2_status,
        l3_status=l3_status,
        l4_status=l4_status,
        l5_status=l5_status,
        pending_llm_layers=pending_llm_layers,
        unresolved_critical=unresolved_critical,
        unresolved_major=unresolved_major,
        unresolved_minor=unresolved_minor,
        revision_rounds=resolved_critical_in_rounds,
        details={
            "min_grounding_score": min_score,
            "fail_on_critical": fail_on_critical,
            "allow_pending_llm_layers": pending_allowed,
            "verdict": verdict,
            "semantic_complete": semantic_complete,
            "pending_llm_layers": pending_llm_layers,
        },
    )
