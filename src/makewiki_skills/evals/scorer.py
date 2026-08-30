"""Deterministic mechanical scoring of a MakeWiki eval run.

This module reads a run-artifact bundle (see :mod:`artifact`) plus the trap's
gold files and computes the §5 mechanical metrics. It is deliberately dumb:
every metric compares *stable identities* — claim IDs, semantic keys, gate
state, an exact literal value — never string similarity, and never any
judgment about prose quality. The semantic metrics (usefulness, native
fluency, troubleshooting plausibility, ...) are left to the LLM Eval Judge
(:mod:`judge`); this module only ever asks "did the run's structured artifacts
make the required claim / assert a forbidden value / stay UNKNOWN."

A run bundle may be produced by a real host running ``/makewiki`` OR by the
fake-LLM fixture driver (:mod:`runner`); the scorer is agnostic either way.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from . import artifact

# Gold files that live beside the trap repo and must NOT be treated as citable
# source evidence (they are the evaluator's fixtures, not the repo under test).
_GOLD_FILES = {
    "verified_facts.json",
    "required_claims.json",
    "forbidden_claims.json",
    "expected_unknowns.json",
    "rubric.yaml",
    "required_entrypoints.json",
}

# ---------------------------------------------------------------------------
# Gold-file loaders (trap fixtures, kept dependency-free)
# ---------------------------------------------------------------------------


class GoldRequiredClaim(BaseModel):
    id: str = ""
    claim_type: str = ""
    semantic_key: str = ""
    assertion: str = ""
    value: str | None = None


class GoldForbiddenClaim(BaseModel):
    id: str = ""
    claim_type: str = ""
    semantic_key: str = ""
    forbidden_assertion: str = ""
    value: str | None = None


class GoldExpectedUnknown(BaseModel):
    id: str = ""
    topic: str = ""
    field: str = ""
    expected_treatment: str = ""


class GoldVerifiedFact(BaseModel):
    id: str = ""
    fact_type: str = ""
    value: str = ""
    source: str = ""
    note: str = ""


class GoldRequiredEntrypoint(BaseModel):
    """One entrypoint that a discovery-correct run MUST surface.

    ``path`` is a repo file (or dir) that must appear as an evidence ref /
    captured fact; ``semantic_key`` is the topic it should feed, when known.
    ``required_entrypoints.json`` is an OPTIONAL discovery gold — a trap that
    omits it simply does not exercise the ``missed_entrypoint_rate`` metric.
    """

    path: str = ""
    semantic_key: str = ""
    note: str = ""


class GoldFiles(BaseModel):
    required: list[GoldRequiredClaim] = Field(default_factory=list)
    forbidden: list[GoldForbiddenClaim] = Field(default_factory=list)
    unknowns: list[GoldExpectedUnknown] = Field(default_factory=list)
    facts: list[GoldVerifiedFact] = Field(default_factory=list)
    entrypoints: list[GoldRequiredEntrypoint] = Field(default_factory=list)


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    import json

    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return list(data)


def load_gold(trap_dir: Path) -> GoldFiles:
    """Load the five gold files from an ``evals/<trap>/`` directory.

    ``required_entrypoints.json`` (when present) is an optional sixth discovery
    gold; its absence simply skips the ``missed_entrypoint_rate`` metric.
    """
    return GoldFiles(
        required=[GoldRequiredClaim(**d) for d in _load_list(trap_dir / "required_claims.json")],
        forbidden=[GoldForbiddenClaim(**d) for d in _load_list(trap_dir / "forbidden_claims.json")],
        unknowns=[GoldExpectedUnknown(**d) for d in _load_list(trap_dir / "expected_unknowns.json")],
        facts=[GoldVerifiedFact(**d) for d in _load_list(trap_dir / "verified_facts.json")],
        entrypoints=[
            GoldRequiredEntrypoint(**d)
            for d in _load_list(trap_dir / "required_entrypoints.json")
        ],
    )


# ---------------------------------------------------------------------------
# Mechanical metric results
# ---------------------------------------------------------------------------


class MetricResult(BaseModel):
    """One §5 mechanical metric outcome with its structured evidence."""

    name: str
    passed: bool
    detail: str = ""
    # Machine-readable counts / identities behind the verdict, so an aggregate
    # can roll up common failure classes without re-reading raw artifacts.
    counts: dict[str, int] = Field(default_factory=dict)
    keys: list[str] = Field(default_factory=list)


class MechanicalScore(BaseModel):
    """Aggregated deterministic score for one run."""

    trap: str
    run_id: str
    metrics: list[MetricResult] = Field(default_factory=list)
    # The single harness-level pass: every required mechanical metric passed.
    mechanical_pass: bool = False
    # Roll-ups that make aggregate/ and the report cheap.
    required_recall: tuple[int, int] = (0, 0)  # (found, total gold required)
    uncorrected_forbidden: int = 0  # forbidden claims still asserted
    unsupported_claim_count: int = 0
    unknown_discipline_broken: int = 0
    evidence_invalid: int = 0

    def metric(self, name: str) -> MetricResult | None:
        return next((m for m in self.metrics if m.name == name), None)


# ---------------------------------------------------------------------------
# Helpers over the run bundle
# ---------------------------------------------------------------------------


class _BundleView(BaseModel):
    """Flat, convenient accessors over a run bundle + docs."""

    meta: artifact.RunMeta
    evidence: artifact.EvidenceArtifact
    agent_claims: artifact.AgentClaimsArtifact
    rebattle: artifact.RebattleArtifact
    adjudications: artifact.AdjudicationsArtifact
    semantic_model: artifact.SemanticModelArtifact
    semantic_audit: artifact.SemanticAuditArtifact
    mechanical_report: artifact.MechanicalReportArtifact
    quality_gate: artifact.QualityGateArtifact
    doc_paths: list[Path] = Field(default_factory=list)

    @property
    def accepted_topics(self) -> set[str]:
        """Semantic keys the Judge accepted (ruling == accepted)."""
        return {r.topic for r in self.adjudications.rulings if r.ruling == "accepted"}

    @property
    def asserted_semantic_keys(self) -> set[str]:
        """Semantic keys that entered the model / were accepted by the Judge."""
        keys = set(self.accepted_topics)
        for ctx in self.semantic_model.claims:
            if ctx.get("semantic_key"):
                keys.add(str(ctx["semantic_key"]))
        return keys

    def final_value_for(self, semantic_key: str) -> str | None:
        """The accepted value for a semantic key, if the Judge supplied one."""
        for r in self.adjudications.rulings:
            if r.topic == semantic_key and r.ruling == "accepted":
                if r.final_assertion:
                    return r.final_assertion
        for ctx in self.semantic_model.claims:
            if str(ctx.get("semantic_key", "")) == semantic_key:
                v = ctx.get("value")
                if v:
                    return str(v)
        return None

    def mechanical_failed_l4a(self) -> list[artifact.CheckArtifact]:
        """L4a mechanical layer FAILED checks (untagged/duplicate blocks)."""
        out: list[artifact.CheckArtifact] = []
        for layer in self.mechanical_report.layers:
            if layer.layer != "L4":
                continue
            for check in layer.checks:
                if check.claim_type == "l4a_mechanical" and check.status == "failed":
                    out.append(check)
        return out

    def mechanical_layer_verdicts(self) -> dict[str, str]:
        return {layer.layer: layer.verdict for layer in self.mechanical_report.layers}

    def pending_semantic_review_ids(self) -> list[str]:
        ids: list[str] = []
        for layer in self.mechanical_report.layers:
            if layer.layer not in ("L3", "L4", "L5"):
                continue
            for check in layer.checks:
                if check.review_item_id and check.status == "pending":
                    ids.append(check.review_item_id)
        return ids

    def cited_paths(self) -> set[str]:
        """Every repo path the run surfaced as evidence: adjudication refs,
        agent-claim refs, and evidence-fact sources. Normalised to
        forward-slash relative paths so a gold entrypoint can be matched
        exactly against what a discovery-correct run actually cited."""
        out: set[str] = set()
        for r in self.adjudications.rulings:
            for ref in r.evidence_refs:
                path_part, _ = _split_line_suffix(ref)
                norm = _strip_ref_prefix(path_part)
                if norm and norm not in _GOLD_FILES:
                    out.add(norm)
        for s in self.agent_claims.sets:
            for claim in s.claims:
                for ref in claim.get("evidence_refs") or []:
                    path_part, _ = _split_line_suffix(str(ref))
                    norm = _strip_ref_prefix(path_part)
                    if norm and norm not in _GOLD_FILES:
                        out.add(norm)
        for fact in self.evidence.facts:
            src = fact.get("source")
            if src:
                norm = _strip_ref_prefix(str(src))
                if norm and norm not in _GOLD_FILES:
                    out.add(_split_line_suffix(norm)[0])
        return out


def _build_view(run_dir: Path) -> _BundleView:
    meta, artifacts = artifact.load_run(run_dir)
    docs_dir = artifact.docs_dir_for(run_dir)
    doc_paths = sorted(docs_dir.glob("*.md")) if docs_dir.is_dir() else []
    return _BundleView(
        meta=meta,
        evidence=artifacts["evidence.json"],  # type: ignore[arg-type]
        agent_claims=artifacts["agent_claims.json"],  # type: ignore[arg-type]
        rebattle=artifacts["rebattle.json"],  # type: ignore[arg-type]
        adjudications=artifacts["adjudications.json"],  # type: ignore[arg-type]
        semantic_model=artifacts["semantic_model.json"],  # type: ignore[arg-type]
        semantic_audit=artifacts["semantic_audit.json"],  # type: ignore[arg-type]
        mechanical_report=artifacts["mechanical_report.json"],  # type: ignore[arg-type]
        quality_gate=artifacts["quality_gate.json"],  # type: ignore[arg-type]
        doc_paths=doc_paths,
    )


def _asserts_value_for(view: _BundleView, semantic_key: str, value: str | None) -> bool:
    """Whether an ACCEPTED entity asserts exactly ``value`` for ``semantic_key``.

    Exact-literal match only (normalized whitespace). This is a structured
    value equality — the port number ``8080`` — never prose similarity.
    """
    if not value:
        return False
    target = " ".join(value.split()).lower()
    actual = view.final_value_for(semantic_key)
    if actual is None:
        return False
    return " ".join(actual.split()).lower() == target


# ---------------------------------------------------------------------------
# Evidence reference resolution (existence + line-range legality)
# ---------------------------------------------------------------------------


def _build_repo_tree(trap_dir: Path) -> tuple[set[str], dict[str, list[str]]]:
    """Recover the trap repo's real file tree, excluding the gold files.

    Returns ``(relative_paths, basename_index)`` where ``relative_paths`` holds
    every source file's normalized forward-slash path (relative to ``trap_dir``)
    and ``basename_index`` maps a bare basename to the relative paths sharing it
    (so an *unambiguous* basename can still resolve a ``server.py`` ref).
    """
    relative_paths: set[str] = set()
    basename_index: dict[str, list[str]] = {}
    for path in sorted(trap_dir.rglob("*")):
        if not path.is_file() or path.name in _GOLD_FILES:
            continue
        rel = path.relative_to(trap_dir).as_posix()
        relative_paths.add(rel)
        basename_index.setdefault(rel.rsplit("/", 1)[-1], []).append(rel)
    return relative_paths, basename_index


def _parse_line_range(suffix: str) -> tuple[int, int | None] | None:
    """Parse a ``N`` or ``N-M`` line range into ``(start, end_or_None)``.

    Returns ``None`` on any malformed suffix. Pure string ops only — no regex —
    per the mechanical-scorer contract (the scorer never regex-matches prose).
    """
    body = suffix.strip()
    if "-" in body:
        parts = body.split("-")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return None
        return int(parts[0]), int(parts[1])
    if body.isdigit():
        return int(body), None
    return None


def _split_line_suffix(ref: str) -> tuple[str, str | None]:
    """Return ``(path, line_suffix_or_None)``.

    A ref is ``path``, ``path:N``, or ``path:N-M``. A trailing ``:``-prefixed
    pure-digit (or ``N-M``) segment is a line range; anything else is left in
    the path so a stray colon is judged on the path's existence, not a bad
    range.
    """
    path, colon, suffix = ref.rpartition(":")
    if not colon or not path or _parse_line_range(suffix) is None:
        return ref, None  # the colon is part of the path, not a range
    return path, suffix


def _count_lines(file_path: Path) -> int:
    with file_path.open(encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh)


def _line_range_in_bounds(file_path: Path, line_suffix: str) -> bool:
    """Whether ``start`` (>= 1, <= EOF) and optional ``end`` (>= start, <= EOF)
    are legal line numbers for the file physically on disk."""
    parsed = _parse_line_range(line_suffix)
    if parsed is None:
        return False
    start, end = parsed
    try:
        n_lines = _count_lines(file_path)
    except OSError:
        return False
    if start < 1 or start > n_lines:
        return False
    if end is not None and (end < start or end > n_lines):
        return False
    return True


def _resolve_ref_path(
    path_part: str,
    repo_paths: set[str],
    basename_index: dict[str, list[str]],
    trap_dir: Path,
) -> Path | None:
    """Resolve a ref's path component to an actual trap-repo file, or ``None``.

    Resolution order: an exact relative path in the trap repo, then an
    *unambiguous* repo basename (used only when the basename appears once).
    Any step only succeeds for a file that genuinely exists in the tree.
    ``../`` traversal cannot slip through: matches come from paths actually
    discovered under ``trap_dir``.
    """
    norm = _strip_ref_prefix(path_part)
    if not norm:
        return None
    if norm in repo_paths:
        return trap_dir / norm
    basename = norm.split("/")[-1]
    candidates = basename_index.get(basename, [])
    if len(candidates) == 1:
        return trap_dir / candidates[0]
    return None


def _resolve_evidence_ref(
    ref: str,
    repo_paths: set[str],
    basename_index: dict[str, list[str]],
    doc_basenames: set[str],
    trap_dir: Path,
) -> bool:
    """True when ``ref`` names a real, existing file with a legal line range."""
    if not ref:
        return True  # empty refs carry no evidence claim; harmless
    path_part, line_part = _split_line_suffix(ref)
    norm = _strip_ref_prefix(path_part)
    if not norm:
        return False
    if norm in doc_basenames:
        # A generated doc (``run_dir/docs/*.md``): a valid citable source whose
        # existence is implied by the bundle, so no disk bounds check applies.
        return True
    file_path = _resolve_ref_path(path_part, repo_paths, basename_index, trap_dir)
    if file_path is None:
        return False
    if line_part is not None and not _line_range_in_bounds(file_path, line_part):
        return False
    return True


def _strip_ref_prefix(path_part: str) -> str:
    """Normalise a ref path: backslashes to slashes, optional leading ``./``
    removed. Unlike a character-class ``lstrip("./")``, a leading dot that is a
    *real filename* (e.g. ``.env``, ``.config/app.yml``) is preserved so hidden
    files resolve exactly."""
    norm = path_part.strip().replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    return norm


def _nval(value: str) -> str:
    """Normalise a value for exact match (whitespace-collapsed, lowercased)."""
    return " ".join(value.split()).lower()


# ---------------------------------------------------------------------------
# The scorer
# ---------------------------------------------------------------------------


def score_run(run_dir: Path, trap_dir: Path) -> MechanicalScore:
    """Score one run bundle against a trap's gold files.

    ``run_dir`` holds a validated run bundle; ``trap_dir`` is ``evals/<trap>/``.
    All metrics are computed from structured identities — never greedily from
    natural-language similarity.
    """
    run_dir = Path(run_dir)
    trap_dir = Path(trap_dir)
    meta, _ = artifact.load_run(run_dir)
    view = _build_view(run_dir)
    gold = load_gold(trap_dir)

    metrics: list[MetricResult] = []

    # Stable identities derived once from the gold fixtures.
    required_keys = {rc.semantic_key for rc in gold.required}

    # -- required claim recall (by stable semantic_key) --------------------
    found, total = 0, len(gold.required)
    missing_required: list[str] = []
    for rc in gold.required:
        if rc.semantic_key in view.asserted_semantic_keys:
            found += 1
        else:
            missing_required.append(rc.semantic_key)
    recall_pass = not missing_required
    metrics.append(
        MetricResult(
            name="required_claim_recall",
            passed=recall_pass,
            detail=f"{found}/{total} required claims present",
            counts={"found": found, "total": total},
            keys=missing_required,
        )
    )

    # -- forbidden claim count ------------------------------------------------
    forbidden_violations: list[str] = []
    for fc in gold.forbidden:
        if fc.value:
            # A value-bearing forbidden claim is violated only by asserting
            # exactly that value (e.g. port 3000 when source says 8080).
            if _asserts_value_for(view, fc.semantic_key, fc.value):
                forbidden_violations.append(fc.semantic_key)
        else:
            # A value-less forbidden claim forbids ANY assertion under its key —
            # but only when that key is not ALSO required (a required+forbidden
            # key is expected to be asserted with the correct value; the "must
            # note the conflict" condition is semantic, left to the LLM judge).
            if (
                fc.semantic_key not in required_keys
                and fc.semantic_key in view.asserted_semantic_keys
            ):
                forbidden_violations.append(fc.semantic_key)
    metrics.append(
        MetricResult(
            name="forbidden_claim_control",
            passed=not forbidden_violations,
            detail=f"{len(forbidden_violations)} forbidden claim(s) still asserted",
            counts={"forbidden": len(forbidden_violations)},
            keys=forbidden_violations,
        )
    )

    # -- expected unknown discipline (a UNKNOWN field is not invented) ------
    # A field must stay UNKNOWN only when it was NOT also required to be
    # established (that would make it resolvable). Asserting such a field —
    # inventing a value with no evidence — is a discipline break. This is fully
    # deterministic: it compares stable semantic keys, never prose.
    unknown_broken: list[str] = []

    for eu in gold.unknowns:
        field = eu.field
        if field in required_keys:
            continue  # resolvable: asserting it is correct, not a break
        asserted = field in view.asserted_semantic_keys or field in view.accepted_topics
        if asserted:
            unknown_broken.append(field)
    metrics.append(
        MetricResult(
            name="unknown_discipline",
            passed=not unknown_broken,
            detail=f"{len(unknown_broken)} expected-UNKNOWN field(s) wrongly asserted",
            counts={"broken": len(unknown_broken)},
            keys=unknown_broken,
        )
    )

    # -- evidence reference validity ---------------------------------------
    # A valid evidence ref names a file that genuinely exists in the trap repo
    # (or is a generated doc), optionally carrying a legal ``:line`` / ``:N-M``
    # range bounded by the real file's line count. This is an existence + bounds
    # check over the real file tree — never a guess from a filename's suffix.
    repo_paths, basename_index = _build_repo_tree(trap_dir)
    doc_basenames = {p.name for p in view.doc_paths if p.is_file()}
    invalid_refs: list[str] = []
    for r in view.adjudications.rulings:
        for ref in r.evidence_refs:
            if not _resolve_evidence_ref(ref, repo_paths, basename_index, doc_basenames, trap_dir):
                invalid_refs.append(ref)
    metrics.append(
        MetricResult(
            name="evidence_reference_validity",
            passed=not invalid_refs,
            detail=f"{len(invalid_refs)} evidence ref(s) that name no existing file / legal line range",
            counts={"invalid": len(invalid_refs)},
            keys=invalid_refs,
        )
    )

    # -- required entrypoints surfaced (discovery; optional gold) ----------
    # A discovery-correct run surfaces every required entrypoint (a hidden
    # .env / .github workflow / nested package / CLI) as a cited path across
    # its adjudications, agent claims, or evidence facts. Skipped when the
    # trap omits required_entrypoints.json — it is an OPTIONAL discovery gold.
    entrypoints = gold.entrypoints
    if entrypoints:
        cited = view.cited_paths()
        missed = []
        for ep in entrypoints:
            if ep.path and ep.path not in cited:
                missed.append(ep.path)
        metrics.append(
            MetricResult(
                name="missed_entrypoint_rate",
                passed=not missed,
                detail=f"{len(entrypoints) - len(missed)}/{len(entrypoints)} required entrypoints surfaced",
                counts={
                    "required": len(entrypoints),
                    "surfaced": len(entrypoints) - len(missed),
                    "missed": len(missed),
                },
                keys=missed,
            )
        )
    else:
        metrics.append(
            MetricResult(
                name="missed_entrypoint_rate",
                passed=True,
                detail="no required_entrypoints.json gold; metric skipped",
                counts={"required": 0, "surfaced": 0, "missed": 0},
            )
        )

    # -- evidence fact coverage (gold facts captured in the evidence bundle) --
    # Every mechanically-discoverable gold fact must be captured in
    # evidence.facts — matched by its stable id, or by its value appearing in
    # the evidence (sources are NOT coupled here, because gold sources often
    # carry a ``:label`` like ``app/cli.py:serve`` that an evidence source does
    # not repeat; the value is the discoverable, stable signal). A gold fact the
    # run's evidence never recorded is a coverage gap — the deterministic
    # evidence layer silently missed a discoverable fact.
    ev_facts = view.evidence.facts
    ev_ids = {str(f.get("id")) for f in ev_facts}
    ev_values = {_nval(str(f.get("value"))) for f in ev_facts}
    uncovered: list[str] = []
    for gf in gold.facts:
        by_id = gf.id in ev_ids
        by_value = _nval(gf.value) in ev_values if gf.value else False
        if not (by_id or by_value):
            uncovered.append(gf.id or gf.value)
    metrics.append(
        MetricResult(
            name="evidence_fact_coverage",
            passed=not uncovered,
            detail=f"{len(gold.facts) - len(uncovered)}/{len(gold.facts)} gold facts captured in evidence",
            counts={"gold": len(gold.facts), "captured": len(gold.facts) - len(uncovered), "missing": len(uncovered)},
            keys=uncovered,
        )
    )

    # -- mechanical Quality Gate state --------------------------------------
    gate = view.quality_gate
    if gate.verdict not in {"passed", "pending_semantic_review", "pending_mechanical_verification", "failed"}:
        gate_state_ok = False
        gate_detail = f"unknown gate verdict {gate.verdict!r}"
    elif gate.verdict == "passed":
        gate_state_ok = gate.semantic_complete and not gate.pending_llm_layers
        gate_detail = "passed requires no pending LLM layers"
    elif gate.verdict == "pending_semantic_review":
        gate_state_ok = not gate.semantic_complete
        gate_detail = "pending_semantic_review implies incomplete semantic audit"
    else:
        gate_state_ok = True
        gate_detail = f"honest non-blocking-or-blocked state {gate.verdict!r}"
    metrics.append(
        MetricResult(
            name="mechanical_gate_state",
            passed=gate_state_ok,
            detail=gate_detail,
            counts={"ci_exit_code": gate.ci_exit_code},
        )
    )

    # -- required workflow presence (by semantic key in the model) ----------
    workflow_keys = {rc.semantic_key for rc in gold.required if rc.claim_type in {"workflow", "command", "prerequisite"}}
    model_keys = set(view.semantic_model.user_tasks) | set(view.semantic_model.troubleshooting)
    missing_wk = sorted(k for k in workflow_keys if k not in view.asserted_semantic_keys and k not in model_keys)
    metrics.append(
        MetricResult(
            name="required_workflow_presence",
            passed=not missing_wk,
            detail=f"{len(workflow_keys) - len(missing_wk)}/{len(workflow_keys)} workflow keys present",
            counts={"missing": len(missing_wk)},
            keys=missing_wk,
        )
    )

    # -- ReBattle discrepancy detected ---------------------------------------
    # A semantic key is "expected to be disputed" when the gold BOTH requires
    # it (must be established) AND forbids a value for it (a conflicting value
    # must not stand). Such contested keys must surface as a ReBattle
    # discrepancy — a fully deterministic stable-key rule, no prose.
    required_keys2 = {rc.semantic_key for rc in gold.required}
    forbidden_keys = {fc.semantic_key for fc in gold.forbidden}
    expected_dispute = required_keys2 & forbidden_keys
    disputed_topics = {d.topic for d in view.rebattle.discrepancies}
    if expected_dispute:
        surfaced = expected_dispute & disputed_topics
        rebattle_ok = len(surfaced) == len(expected_dispute)
        rebattle_detail = f"surfaced {len(surfaced)}/{len(expected_dispute)} expected disputes"
    else:
        rebattle_ok = True
        rebattle_detail = "no contested semantic key in this trap"
    metrics.append(
        MetricResult(
            name="rebattle_discrepancy_detected",
            passed=rebattle_ok,
            detail=rebattle_detail,
            counts={"expected": len(expected_dispute), "surfaced": len(expected_dispute & disputed_topics)},
            keys=sorted(expected_dispute - disputed_topics),
        )
    )

    # -- Judge output presence (semantic-key coverage, not counts) ----------
    # Every semantic topic that entered ReBattle must receive a Judge ruling on
    # that same topic. Comparing raw counts would be gameable — an unrelated
    # ruling on a different topic could mask a missing disputed-topic ruling —
    # so coverage is keyed on the semantic topic itself. A ruling on a topic
    # that was never disputed is harmless, but never substitutes for a missing
    # disputed-topic ruling.
    disputed_topics = {d.topic for d in view.rebattle.discrepancies}
    ruled_topics = {r.topic for r in view.adjudications.rulings}
    missing_ruled = sorted(disputed_topics - ruled_topics)
    judge_ok = not missing_ruled
    metrics.append(
        MetricResult(
            name="judge_output_presence",
            passed=judge_ok,
            detail=f"{len(ruled_topics)} ruled topic(s) for {len(disputed_topics)} disputed topic(s)",
            counts={
                "rulings": len(view.adjudications.rulings),
                "disputes": len(view.rebattle.discrepancies),
                "covered": len(disputed_topics & ruled_topics),
                "disputed": len(disputed_topics),
            },
            keys=missing_ruled,
        )
    )

    # -- stable block parity (no L4a failures; code blocks identical) -------
    l4a_failed = view.mechanical_failed_l4a()
    block_parity_ok = not l4a_failed
    block_parity_detail = f"{len(l4a_failed)} L4a failure(s)" if l4a_failed else "all technical blocks tagged"
    metrics.append(
        MetricResult(
            name="stable_block_parity",
            passed=block_parity_ok,
            detail=block_parity_detail,
            counts={"l4a_failed": len(l4a_failed)},
        )
    )

    # -- audit completeness (gate passed <=> audit covers all pending) ------
    pending_review = view.pending_semantic_review_ids()
    audited_ids = {v.review_item_id for v in view.semantic_audit.verdicts}
    if gate.verdict == "passed":
        audit_ok = (not pending_review)
        audit_detail = "gate passed with no pending semantic review items"
    else:
        audit_ok = True
        audit_detail = f"gate {gate.verdict!r}; {len(pending_review)} item(s) still pending"
    metrics.append(
        MetricResult(
            name="audit_completeness",
            passed=audit_ok,
            detail=audit_detail,
            counts={"pending": len(pending_review), "audited": len(audited_ids)},
        )
    )

    mechanical_pass = all(m.passed for m in metrics)
    return MechanicalScore(
        trap=meta.trap,
        run_id=meta.run_id,
        metrics=metrics,
        mechanical_pass=mechanical_pass,
        required_recall=(found, total),
        uncorrected_forbidden=len(forbidden_violations),
        unsupported_claim_count=len(forbidden_violations),
        unknown_discipline_broken=len(unknown_broken),
        evidence_invalid=len(invalid_refs),
    )
