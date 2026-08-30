"""Quality Gate: single gate over all L0-L5 verification layers.

The Quality Gate aggregates the per-layer reports produced by
``VerificationOrchestrator`` into one decision — PASS / FAIL /
PENDING_SEMANTIC_REVIEW / PENDING_MECHANICAL_VERIFICATION — that the CLI maps
to a CI exit code and the Skill layer consults before shipping a document set.

Python verifies what can be mechanically proven (L0/L1/L2 + L4a mechanical
parity). L3 behavior, L4b prose-parity and L5 epistemic review are LLM-judged;
when any of them is still ``pending`` the gate reports
``verdict="pending_semantic_review"`` and ``semantic_complete=False`` so the
pending state is never hidden. When a mechanical layer is itself pending (not
yet failed but unproven) the gate reports ``verdict="pending_mechanical_
verification"``. When a mechanical layer fails the gate is ``failed``.

Honesty contract: ``passed`` is *strictly* ``verdict == "passed"``. A pending
gate is NEVER ``passed=True``. The ``ci_exit_code`` is the single exit policy
source: ``passed -> 0``, ``failed -> 1``, ``pending_semantic_review -> 0/2``
(``0`` when ``allow_pending_llm_layers`` grants the exit policy, ``2`` as the
honest base otherwise), ``pending_mechanical_verification -> 3``. The legacy
``exit_code`` property is retained as an alias of ``ci_exit_code``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.verification.report import (
    ComprehensiveVerificationReport,
    VerificationCheck,
)

# Gate verdicts, most to least permissive:
#   passed                          - every layer adjudicated and non-blocking.
#   pending_semantic_review         - LLM layer (L3/L4b/L5) still pending.
#   pending_mechanical_verification - mechanical layer (L0/L1/L2/L4a) still pending.
#   failed                          - a mechanical or LLM layer explicitly failed.
QualityGateVerdict = Literal[
    "passed",
    "pending_semantic_review",
    "pending_mechanical_verification",
    "failed",
]

#: Marker for a pending mechanical-verification state (CI conveys it distinctly).
GateState = Literal[
    "passed", "failed", "pending", "not_applicable"
]


def ci_exit_code_for(
    verdict: QualityGateVerdict,
    allow_pending_llm_layers: bool = True,
) -> int:
    """Map a gate verdict to a CI exit code.

    Honest base mapping: ``passed -> 0``, ``failed -> 1``,
    ``pending_semantic_review -> 2``, ``pending_mechanical_verification -> 3``.

    EXIT POLICY ONLY: when ``allow_pending_llm_layers`` is True (the default),
    a ``pending_semantic_review`` verdict exits 0 — the review is not a
    mechanical failure — while the UI/verdict still reads PENDING_SEMANTIC_REVIEW.
    """
    if verdict == "passed":
        return 0
    if verdict == "failed":
        return 1
    if verdict == "pending_semantic_review":
        return 0 if allow_pending_llm_layers else 2
    # pending_mechanical_verification
    return 3


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
    # Coverage ratio (0..1) of LLM-adjudicated checks (L3/L4b/L5) that passed.
    # This is NOT a Python-computed semantic score: it is a mechanical COUNT of
    # how many semantic checks the LLM Auditor marked passed out of those it
    # adjudicated. None while any LLM layer is still pending (unadjudicated).
    # The semantic QUALITY of the content is scored by the LLM Eval Judge, never
    # here — Python only measures adjudication coverage.
    semantic_coverage: float | None = None
    l0_status: str = "pending"
    l1_status: str = "pending"
    l2_status: str = "pending"
    l3_status: str = "pending"
    l4_status: str = "pending"
    l4a_status: str = "pending"
    l4b_status: str = "pending"
    l5_status: str = "pending"
    pending_llm_layers: list[str] = Field(default_factory=list)
    pending_mechanical_layers: list[str] = Field(default_factory=list)
    ci_exit_code: int = 0

    @property
    def exit_code(self) -> int:
        """CI exit code.

        Backward-compatible alias of ``ci_exit_code`` — the honest,
        exit-policy-aware mapping (0/1/2/3).
        """
        return self.ci_exit_code


def _layer_status(
    report: ComprehensiveVerificationReport, layer: str
) -> Literal["passed", "failed", "pending", "not_applicable"]:
    layer_report = report.layers.get(layer)
    if layer_report is None:
        return "pending"
    return layer_report.verdict


def _l4_checks(report: ComprehensiveVerificationReport) -> list[VerificationCheck]:
    l4 = report.layers.get("L4")
    if l4 is None:
        return []
    return list(l4.checks)


def _l4a_mechanical_checks(
    report: ComprehensiveVerificationReport,
) -> list[VerificationCheck]:
    """The L4 checks that are mechanically decidable (stable-block + fact parity)."""
    return [c for c in _l4_checks(report) if c.claim_type == "l4a_mechanical"]


def _l4b_semantic_checks(
    report: ComprehensiveVerificationReport,
) -> list[VerificationCheck]:
    """The L4 checks that are LLM-judged prose parity (``l4b_semantic``)."""
    return [c for c in _l4_checks(report) if c.claim_type == "l4b_semantic"]


def _subset_status(
    checks: list[VerificationCheck],
) -> Literal["passed", "failed", "pending", "not_applicable"]:
    """Honest status for a subset of checks filtered out of a layer.

    Mirrors ``LayerReport.verdict`` semantics over a filtered subset: an empty
    subset is ``not_applicable`` (there is nothing of that kind to verify, so it
    does not hold the gate pending). A layer is never ``passed`` merely because
    it has no failures.
    """
    if not checks:
        return "not_applicable"
    if any(c.status == "failed" for c in checks):
        return "failed"
    if any(c.status in ("pending", "unknown") for c in checks):
        return "pending"
    if all(c.status == "not_applicable" for c in checks):
        return "not_applicable"
    if any(c.verified for c in checks):
        return "passed"
    return "pending"


def _score(passed: int, total: int) -> float:
    return round(passed / total, 3) if total else 1.0


def evaluate_quality_gate(
    report: ComprehensiveVerificationReport,
    config: MakeWikiConfig | None = None,
    *,
    min_grounding_score: float | None = None,
    resolved_critical_in_rounds: int = 0,
    allow_pending_llm_layers: bool | None = None,
    revision: Any = None,
) -> QualityGateResult:
    """Evaluate a comprehensive report against configurable quality thresholds.

    Parameters
    ----------
    report:
        The aggregate L0-L5 report from the orchestrator.
    config:
        Optional configuration. A full ``MakeWikiConfig`` supplies the gate's
        single grounding threshold from ``quality.min_grounding_score`` (and
        ``quality.allow_pending_llm_layers`` when the flag is None).
    min_grounding_score:
        Explicit override for the grounding threshold. When None, the gate
        inherits it from ``config.quality.min_grounding_score`` (or default 1.0).
    allow_pending_llm_layers:
        EXIT POLICY ONLY — never changes the truth verdict. When True (default),
        unresolved LLM-judged layers (L3 / L4b / L5) that are pending hold the
        gate at ``pending_semantic_review`` and exit 0. When False, the verdict
        STILL reads ``pending_semantic_review`` (never ``failed``) but the honest
        base exit code is 2.
    revision:
        Backward-compatibility alias for ``config``.
    """
    cfg = config if config is not None else (revision if isinstance(revision, MakeWikiConfig) else None)
    min_score = min_grounding_score
    if min_score is None:
        if isinstance(cfg, MakeWikiConfig):
            min_score = cfg.quality.min_grounding_score
        else:
            min_score = 1.0

    pending_allowed = allow_pending_llm_layers
    if pending_allowed is None and isinstance(cfg, MakeWikiConfig):
        pending_allowed = cfg.quality.allow_pending_llm_layers
    if pending_allowed is None:
        pending_allowed = True

    # ---- per-layer honest status --------------------------------------------
    l0_status = _layer_status(report, "L0")
    l1_status = _layer_status(report, "L1")
    l2_status = _layer_status(report, "L2")
    l3_status = _layer_status(report, "L3")
    l4_status = _layer_status(report, "L4")
    l5_status = _layer_status(report, "L5")
    # L4 split: L4a (mechanical parity) is a mechanical layer; L4b (semantic
    # prose parity) is an LLM layer.
    l4a_checks = _l4a_mechanical_checks(report)
    l4b_checks = _l4b_semantic_checks(report)
    l4a_status = _subset_status(l4a_checks)
    l4b_status = _subset_status(l4b_checks)

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
        "L4b": l4b_status,
        "L5": l5_status,
    }
    pending_llm_layers = [
        name for name, st in llm_statuses.items() if st in ("pending", "unknown")
    ]
    semantic_complete = not bool(pending_llm_layers)

    if pending_llm_layers:
        semantic_coverage: float | None = None
    else:
        sem_total = 0
        sem_passed = 0
        l3 = report.layers.get("L3")
        if l3 is not None:
            sem_total += l3.total_checks
            sem_passed += l3.passed_count
        sem_total += len(l4b_checks)
        sem_passed += sum(1 for c in l4b_checks if c.verified)
        l5 = report.layers.get("L5")
        if l5 is not None:
            sem_total += l5.total_checks
            sem_passed += l5.passed_count
        # Coverage of LLM-adjudicated checks only — a mechanical count, never a
        # Python-authored semantic rating (the LLM Eval Judge owns semantic
        # quality).
        semantic_coverage = _score(sem_passed, sem_total)

    # ---- unresolved counts (severity-differentiated) -------------------------
    mechanical_failed_count = sum(
        report.layers[n].failed_count
        for n in ("L0", "L1", "L2")
        if n in report.layers
    ) + sum(1 for c in l4a_checks if c.status == "failed")
    llm_failed = sum(
        report.layers[n].failed_count
        for n in ("L3", "L5")
        if n in report.layers
    ) + sum(1 for c in l4b_checks if c.status == "failed")
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
    # Mechanical layers (L0/L1/L2/L4a) still pending — not yet failed but
    # unproven. A pending mechanical layer withholds "passed" and is reported as
    # PENDING_MECHANICAL_VERIFICATION so it is never conflated with the LLM.
    mechanical_statuses = {
        "L0": l0_status,
        "L1": l1_status,
        "L2": l2_status,
        "L4a": l4a_status,
    }
    pending_mechanical_layers = [
        name for name, st in mechanical_statuses.items() if st == "pending"
    ]
    mechanical_pending = bool(pending_mechanical_layers)

    # ---- verdict (honest) ----------------------------------------------------
    # A mechanical-layer failure OR a mechanical-score shortfall drives "failed";
    # so does an EXPLICIT LLM-judged layer failure (a documented check that
    # contradicted or was never proven cannot be papered over). A pending
    # mechanical layer drives PENDING_MECHANICAL_VERIFICATION. Otherwise a
    # pending LLM layer holds the gate at PENDING_SEMANTIC_REVIEW — the verdict
    # NEVER flips to "failed" for an un-reviewed semantic item. Whether the exit
    # policy grants that pending state a 0 or a 2 is decided separately by
    # ``ci_exit_code_for``/``allow_pending_llm_layers`` (exit policy only). Only
    # a fully adjudicated, non-blocking report is "passed".
    if any_mechanical_failed or llm_failed:
        verdict: QualityGateVerdict = "failed"
    elif mechanical_pending:
        # A pending mechanical layer (L0/L1/L2/L4a) withholds PASS and is
        # reported as PENDING_MECHANICAL_VERIFICATION — not failed (it has not
        # yet failed, only unproven) and not conflated with the LLM.
        verdict = "pending_mechanical_verification"
    elif not meets_score:
        # Score shortfall not explained by an explicit pending gap (defensive:
        # a dip in the mechanical score with no pending/failed layer).
        verdict = "failed"
    elif pending_llm_layers:
        # A pending LLM layer (L3/L4b/L5) with no audit verdict is ALWAYS
        # ``pending_semantic_review``. ``allow_pending_llm_layers`` is EXIT
        # POLICY ONLY and can never change the truth verdict from pending to
        # failed: it only maps to exit 0 (allowed) or exit 2 (not allowed) in
        # ``ci_exit_code_for``. Python never converts an un-reviewed semantic
        # item into a failure.
        verdict = "pending_semantic_review"
    else:
        verdict = "passed"

    # ---- honesty contract (strict) ------------------------------------------
    # ``passed`` is EXACTLY ``verdict == "passed"``. A pending gate is never
    # passed — the historical decoupling (pending-but-passed=True) is removed.
    passed = verdict == "passed"

    ci_exit_code = ci_exit_code_for(verdict, pending_allowed)

    return QualityGateResult(
        passed=passed,
        verdict=verdict,
        ci_exit_code=ci_exit_code,
        syntax_passed=syntax_passed,
        existence_passed=existence_passed,
        interface_passed=interface_passed,
        behavior_passed=behavior_passed,
        cross_language_passed=cross_language_passed,
        epistemic_passed=epistemic_passed,
        # ``mechanical_passed`` is TRUE only when every mechanical plane is
        # genuinely proven, NOT merely un-failed: L0/L1/L2 must be passed, L4a
        # must be passed or not_applicable (a PENDING L4a must NOT count as
        # passed), and the grounding threshold must be met. It is independent of
        # the LLM semantic state, so a pending L3/L4b/L5 does not drag it down.
        mechanical_passed=(
            all_mechanical and l4a_status in ("passed", "not_applicable") and meets_score
        ),
        semantic_complete=semantic_complete,
        grounding_score=grounding_score,
        mechanical_score=mechanical_score,
        semantic_coverage=semantic_coverage,
        l0_status=l0_status,
        l1_status=l1_status,
        l2_status=l2_status,
        l3_status=l3_status,
        l4_status=l4_status,
        l4a_status=l4a_status,
        l4b_status=l4b_status,
        l5_status=l5_status,
        pending_llm_layers=pending_llm_layers,
        pending_mechanical_layers=pending_mechanical_layers,
        unresolved_critical=unresolved_critical,
        unresolved_major=unresolved_major,
        unresolved_minor=unresolved_minor,
        revision_rounds=resolved_critical_in_rounds,
        details={
            "min_grounding_score": min_score,
            "allow_pending_llm_layers": pending_allowed,
            "verdict": verdict,
            "ci_exit_code": ci_exit_code,
            "semantic_complete": semantic_complete,
            "pending_llm_layers": pending_llm_layers,
            "pending_mechanical_layers": pending_mechanical_layers,
        },
    )
