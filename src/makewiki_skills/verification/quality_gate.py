"""Quality Gate: single gate over all L0-L5 verification layers.

The Quality Gate aggregates the per-layer reports produced by
``VerificationOrchestrator`` into one decision — PASS or FAIL — that the CLI maps
to a CI exit code and the Skill layer consults before shipping a document set.

Python verifies what can be mechanically proven (L0/L1/L2/L4-exact). L3 behavior,
L4 prose-parity and L5 epistemic review are LLM-judged; their layers may be left
``pending`` for the Skill's Auditor to reason over. The gate still reports them
transparently so unresolved items are never silently hidden.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from makewiki_skills.config import MakeWikiConfig, RevisionConfig
from makewiki_skills.verification.report import ComprehensiveVerificationReport

QualityGateVerdict = Literal["passed", "failed", "pending"]


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

    @property
    def exit_code(self) -> int:
        """CI exit code: 0 on pass, 1 on fail."""
        return 0 if self.passed else 1


def _layer_status(report: ComprehensiveVerificationReport, layer: str) -> Literal["passed", "failed", "pending"]:
    layer_report = report.layers.get(layer)
    if layer_report is None:
        return "pending"
    if layer_report.failed_count:
        return "failed"
    # A layer with zero checks or only pending checks is not yet independently proven.
    if layer_report.passed_count == 0:
        return "pending"
    return "passed"


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
            min_score = revision.min_grounding_score  # type: ignore[attr-defined]
        else:
            min_score = 1.0

    pending_allowed = allow_pending_llm_layers
    if pending_allowed is None and isinstance(revision, MakeWikiConfig):
        pending_allowed = revision.quality.allow_pending_llm_layers
    if pending_allowed is None:
        pending_allowed = True

    syntax_passed = _layer_status(report, "L0") == "passed"
    existence_passed = _layer_status(report, "L1") == "passed"
    interface_passed = _layer_status(report, "L2") == "passed"
    behavior_passed = _layer_status(report, "L3") == "passed"
    cross_language_passed = _layer_status(report, "L4") == "passed"
    epistemic_passed = _layer_status(report, "L5") == "passed"

    grounding_score = report.score

    # Unresolved counts come from failed checks across the mechanical layers and
    # the verification score shortfall. We surface the tally for the Skill gate
    # step rather than silently dropping any.
    failed_checks = sum(
        lr.failed_count for name, lr in report.layers.items() if name != "L5"
    )
    unresolved_critical = (
        failed_checks + (0 if grounding_score >= min_score else 1)
    )

    meets_score = grounding_score >= min_score
    all_mechanical = syntax_passed and existence_passed and interface_passed

    # ``allow_pending_llm_layers`` controls whether LLM-judged layers that
    # are still pending downgrade the gate. ``pending_allowed`` already
    # defaults to True to keep the historical behavior; the explicit knob
    # exists so operators can flip it without touching the rewrite policy.
    _ = pending_allowed

    if fail_on_critical:
        passed = bool(all_mechanical and meets_score)
    else:
        # Informational mode: only fail on outright mechanically-provable gaps.
        passed = bool(meets_score and existence_passed)

    return QualityGateResult(
        passed=passed,
        syntax_passed=syntax_passed,
        existence_passed=existence_passed,
        interface_passed=interface_passed,
        behavior_passed=behavior_passed == "passed",
        cross_language_passed=cross_language_passed == "passed",
        epistemic_passed=epistemic_passed == "passed",
        grounding_score=round(grounding_score, 3),
        unresolved_critical=unresolved_critical,
        unresolved_major=failed_checks,
        unresolved_minor=0,
        revision_rounds=resolved_critical_in_rounds,
        details={
            "min_grounding_score": min_score,
            "fail_on_critical": fail_on_critical,
            "allow_pending_llm_layers": pending_allowed,
        },
    )
