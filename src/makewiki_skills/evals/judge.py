"""LLM rubric-judge protocol (schema + input assembly only).

The §6 semantic metrics — workflow correctness, documentation usefulness,
native-language quality, troubleshooting correctness, semantic parity,
epistemic calibration — are judged by an INDEPENDENT LLM Eval Judge, never by
Python. This module is the *protocol* around that judge:

* it loads ``evals/<trap>/rubric.yaml`` into a typed rubric;
* it assembles the judge's input bundle (gold rubric + required evidence +
  the writer docs) so any host has a stable, machine-readable prompt payload;
* it validates the judge's returned structured verdict bundle, so downstream
  aggregation sees a fixed schema;

but it performs NO semantic reasoning itself. A ``semantic_score`` field of the
verdict is populated ONLY from the judge's own JSON output — never derived here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, model_validator

# The §6 semantic metrics that require an LLM judge (never Python).
SEMANTIC_METRICS = (
    "workflow_correctness",
    "documentation_usefulness",
    "native_language_quality",
    "troubleshooting_correctness",
    "semantic_parity",
    "epistemic_calibration",
)

JUDGE_VERDICT_FILE = "judge_bundle.json"


class RubricMetric(BaseModel):
    name: str
    weight: float = 0.0
    required: bool = False


class Rubric(BaseModel):
    """Typed view of ``evals/<trap>/rubric.yaml``."""

    trap: str = ""
    description: str = ""
    metrics: dict[str, RubricMetric] = Field(default_factory=dict)
    pass_threshold: float = 0.8
    passes_when: str = ""
    runs: int = 3


def load_rubric(trap_dir: Path) -> Rubric:
    """Parse a trap's rubric.yaml into a typed Rubric."""
    path = trap_dir / "rubric.yaml"
    raw: dict[str, Any] = {}
    if path.is_file():
        with path.open(encoding="utf-8") as fh:
            raw = (yaml.safe_load(fh) or {}) or {}
    metrics: dict[str, RubricMetric] = {}
    for name, spec in (raw.get("metrics") or {}).items():
        if isinstance(spec, dict):
            metrics[name] = RubricMetric(
                name=name,
                weight=float(spec.get("weight", 0.0)),
                required=bool(spec.get("required", False)),
            )
        else:
            metrics[name] = RubricMetric(name=name)
    scoring = raw.get("scoring") or {}
    return Rubric(
        trap=str(raw.get("trap", trap_dir.name)),
        description=str(raw.get("description", "")),
        metrics=metrics,
        pass_threshold=float(scoring.get("pass_threshold", 0.8)),
        passes_when=str(scoring.get("passes_when", "")),
        runs=int(scoring.get("runs", 3)),
    )


# ---------------------------------------------------------------------------
# Judge input assembly (host-agnostic prompt payload)
# ---------------------------------------------------------------------------


def _normalize_metric_key(name: str) -> str:
    """Mechanical normalization of a metric key: lowercase, non-alphanumerics
    to underscores. Lets a rubric written with human-readable names
    ("Native-language Quality") map onto the protocol's fixed
    ``SEMANTIC_METRICS`` keys ("native_language_quality") without any fuzzy or
    semantic matching."""
    return "".join(c if c.isalnum() else "_" for c in name.strip().lower())


def assemble_judge_input(
    trap_dir: Path,
    run_dir: Path,
    *,
    mechanical_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the machine-readable bundle handed to the LLM Eval Judge.

    The bundle contains the gold rubric, the semantic metrics to grade, the
    writer docs (sources of the prose being judged), and optional mechanical
    evidence. Assembling this is mechanical; grading it is the judge's job.

    The bundled docs are the run's ``docs/*.md`` — joined by filename so the
    judge sees the per-language writer output without the harness duplicating
    any semantic reading of them.
    """
    rubric = load_rubric(trap_dir)
    # Rubric metric names may be written in human form ("Native-language
    # Quality"); map them mechanically onto the protocol's fixed metric keys so
    # a real rubric actually drives the judge's weights.
    normalized = {_normalize_metric_key(k): v for k, v in rubric.metrics.items()}
    docs: dict[str, str] = {}
    docs_dir = run_dir / "docs"
    if docs_dir.is_dir():
        for md in sorted(docs_dir.glob("*.md")):
            docs[md.name] = md.read_text(encoding="utf-8", errors="replace")
    # Weights come from the rubric under its human-readable name, defaulting to
    # 0.0 when the rubric does not grade a given semantic metric.
    semantic_weights: dict[str, float] = {}
    for metric in SEMANTIC_METRICS:
        entry = normalized.get(metric)
        semantic_weights[metric] = entry.weight if entry is not None else 0.0
    return {
        "trap": rubric.trap,
        "gold_rubric": rubric.model_dump(),
        "semantic_metrics": semantic_weights,
        "passes_when": rubric.passes_when,
        "docs": docs,
        "mechanical_evidence": mechanical_evidence or {},
    }


# ---------------------------------------------------------------------------
# Judge verdict bundle (schema + validation)
# ---------------------------------------------------------------------------


class JudgeAreaVerdict(BaseModel):
    """One per-metric verdict from the LLM judge."""

    metric: str
    score: float = Field(  # 0..1; supplied by the judge, never computed here
        ge=0.0,
        le=1.0,
    )
    note: str = ""


class JudgeVerdict(BaseModel):
    """Structured, machine-readable output of one LLM Eval Judge pass.

    ``each_score`` is the judge's own 0..1 rating per semantic metric. Aggregates
    may only average these; Python never fabricates a semantic rating when the
    judge bundle is absent.
    """

    trap: str
    judge_id: str = ""
    model: str = ""  # which host model judged (informational)
    each: list[JudgeAreaVerdict] = Field(default_factory=list)
    overall: float = Field(  # judge's own weighted overall (0..1)
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode="after")
    def _reject_duplicate_metrics(self) -> JudgeVerdict:
        seen: set[str] = set()
        for v in self.each:
            if v.metric in seen:
                raise ValueError(f"duplicate metric in judge verdict: {v.metric!r}")
            seen.add(v.metric)
        return self

    def score_for(self, metric: str) -> float | None:
        for v in self.each:
            if v.metric == metric:
                return v.score
        return None


def validate_required_metrics(verdict: JudgeVerdict, rubric: Rubric) -> list[str]:
    """Return rubric metrics marked ``required=True`` that are MISSING from the
    verdict's ``each`` list (empty list = all present).

    A judge bundle ONLY grades the semantic metrics (``SEMANTIC_METRICS``), never
    the mechanical ones (recall / unsupported rate / evidence grounding, which
    the mechanical scorer measures instead). So a rubric metric only holds a
    judge bundle *incomplete* when it is both marked ``required`` AND is a
    semantic metric the judge was supposed to grade. A required mechanical
    metric is enforced by the scorer, not the judge; its absence from a judge
    bundle is expected and never "incomplete".

    This is a cross-object (rubric + verdict) check, so it lives here as a plain
    function rather than in the pydantic model, which does not know the rubric.

    The rubric may spell a metric in human form ("Native-language Quality") while
    the protocol's canonical key is "native_language_quality". Both sides are
    run through the SAME :func:`_normalize_metric_key` used by
    :func:`assemble_judge_input`, so a required metric matches regardless of
    spelling — there is exactly one normalization path, never two that can drift
    apart. Matching remains mechanical, never semantic.
    """
    semantic_required = {
        _normalize_metric_key(name)
        for name, spec in rubric.metrics.items()
        if spec.required and _normalize_metric_key(name) in SEMANTIC_METRICS
    }
    present = {_normalize_metric_key(v.metric) for v in verdict.each}
    missing = sorted(semantic_required - present)
    return missing


def save_judge_verdict(run_dir: Path, verdict: JudgeVerdict) -> Path:
    """Persist a judge verdict bundle inside a run directory."""
    path = run_dir / JUDGE_VERDICT_FILE
    path.write_text(json.dumps(verdict.model_dump(), indent=2), encoding="utf-8")
    return path


def load_judge_verdict(run_dir: Path) -> JudgeVerdict | None:
    """Read a run's judge bundle, or None when absent (no LLM judged it)."""
    path = run_dir / JUDGE_VERDICT_FILE
    if not path.is_file():
        return None
    return JudgeVerdict.model_validate_json(path.read_text(encoding="utf-8"))
