"""Authoritative full-handoff integration test driven by FAKE LLM actors.

This is the gap-layer suite: it proves the *authoritative* chain works end to end
using fakes, with NO real model calls and no network. It exercises the real
Python mechanical plane (evidence scanner, ReBattle dispute machinery, semantic
model folding, L0-L5 verifier, Quality Gate, SemanticAuditBundle digest binding)
and simulates every LLM role with deterministic stand-ins:

    Repository Fixture
      -> EvidenceCollector / build_claims_from_evidence  (EvidenceFacts /
         MechanicalAssertions, provenance="python_fact")
      -> AgentClaimBundle (AgentClaimSet)                 (fake LLM scouts)
      -> ReBattleArena.detect_discrepancies               (real dispute organizer)
      -> AdjudicationResults (fake Judge) + synthesize_consensus
      -> fold_adjudicated_into_semantic_model             (authoritative model)
      -> fake LLM-writer Markdown (ID-tagged code blocks)
      -> VerificationOrchestrator.verify_documents        (real L0-L5)
      -> SemanticAuditBundle (fake LLM Auditor) folded in by Python
      -> evaluate_quality_gate                            (real gate)

The honest-state tests pin the Cognitive Authority Boundary on the LLM side:
a stale or absent audit bundle can never produce a vacuous ``passed`` verdict —
the semantic layers (L3/L4b/L5) simply stay ``pending_semantic_review``.
"""

from __future__ import annotations

from pathlib import Path

import makewiki_skills.config as config_mod
from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.model.claim import build_claims_from_evidence
from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.model.rebattle import (
    AdjudicationResult,
    AgentClaim,
    AgentClaimSet,
    ReBattleArena,
    fold_adjudicated_into_semantic_model,
)
from makewiki_skills.model.semantic_model import SemanticModel
from makewiki_skills.scanner.evidence_collector import EvidenceCollector
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetector
from makewiki_skills.verification.orchestrator import VerificationOrchestrator
from makewiki_skills.verification.quality_gate import ci_exit_code_for, evaluate_quality_gate
from makewiki_skills.verification.report import VerificationCheck
from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    SemanticAuditVerdict,
    bundle_matches_documents,
    compute_documents_digest,
)

# ---------------------------------------------------------------------------
# Fixture / helpers
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path) -> Path:
    """Build a tiny synthetic repository: Makefile + config + README (+ a CLI)."""
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / "Makefile").write_text(
        """.PHONY: build test
build:
\tgcc -o app main.c
test:
\tmake -q
""",
        encoding="utf-8",
    )
    (proj / "config.yaml").write_text("server:\n  port: 8080\n", encoding="utf-8")
    (proj / "pyproject.toml").write_text(
        '[project]\nname="myapp"\nversion="1.0.0"\n'
        '[project.scripts]\nmyapp="cli:main"\n',
        encoding="utf-8",
    )
    # A small Typer CLI so the L2 interface verifier has a real command spec to
    # match against (an empty L2 layer would otherwise report ``pending``).
    (proj / "cli.py").write_text(
        'import typer\napp=typer.Typer()\n'
        '@app.command()\ndef run(port:int=8080, host:str="0.0.0.0"):\n    print(port)\n'
        '@app.command()\ndef serve():\n    print("s")\n'
        'def main():\n    app()\n',
        encoding="utf-8",
    )
    (proj / "README.md").write_text("# myapp\n\nmyapp is a tiny app.\n", encoding="utf-8")
    return proj


# Fake LLM-writer markdown. Every TECHNICAL code block (bash) carries a stable
# ``[[id:...]]`` marker and is byte-identical across languages so the mechanical
# L4a (stable-block + untagged-block audit) layer passes cleanly.
_EN_BODY = """# myapp

myapp is a tiny scaffold.

<!-- makewiki:section=build -->
## Build

[[id:build]]
```bash
make build
```

<!-- makewiki:section=test -->
## Test

[[id:test]]
```bash
make test
```

<!-- makewiki:section=run -->
## Run

[[id:run]]
```bash
myapp run --port 8080
```

<!-- makewiki:section=configure -->
## Configure

Set `server.port` in `./config.yaml`.
"""

_ZH_BODY = _EN_BODY.replace("myapp is a tiny scaffold.", "myapp 是一个微型脚手架。")


def _writer_docs(
    tmp_path: Path,
    *,
    en_body: str | None = None,
    zh_body: str | None = None,
) -> tuple[Path, dict[str, list[DocumentArtifact]]]:
    """Write fake LLM-writer markdown to disk and build DocumentArtifacts."""
    writer = tmp_path / "writer"
    writer.mkdir(exist_ok=True)
    en_body = _EN_BODY if en_body is None else en_body
    zh_body = _ZH_BODY if zh_body is None else zh_body
    (writer / "README.md").write_text(en_body, encoding="utf-8")
    (writer / "README.zh-CN.md").write_text(zh_body, encoding="utf-8")
    docs = {
        "en": [
            DocumentArtifact(
                filename="README.md", base_name="README",
                language_code="en", content=en_body,
            )
        ],
        "zh-CN": [
            DocumentArtifact(
                filename="README.zh-CN.md", base_name="README",
                language_code="zh-CN", content=zh_body,
            )
        ],
    }
    return writer, docs


def _writer_paths(writer: Path) -> list[Path]:
    return [writer / "README.md", writer / "README.zh-CN.md"]


def _engineer_evidence(
    proj: Path,
) -> tuple[dict[str, object], EvidenceRegistry]:
    """Run the real Python evidence scanner over the repo fixture.

    Returns (detection-data, registry) of ``EvidenceFacts``; the mechanical
    assertions are built via ``build_claims_from_evidence``.
    """
    config = MakeWikiConfig.default(proj)
    detection = ProjectDetector().detect(proj)
    collected = EvidenceCollector(config).collect(proj, detection)
    registry = EvidenceRegistry()
    registry.add_many(collected.facts)
    return {"detection": detection, "config": config}, registry


def _scout_claim_sets() -> list[AgentClaimSet]:
    """Fake LLM scouts: two perspectives disagree on the port, agree on the wrkfl."""
    red = AgentClaimSet(
        agent_id="agent_red",
        perspective="user_experience",
        claims=[
            AgentClaim(
                agent_id="agent_red",
                claim_type="config",
                semantic_key="network.port",
                assertion="The app listens on port 3000",
                value="3000",
                confidence="low",
            ),
            AgentClaim(
                agent_id="agent_red",
                claim_type="workflow",
                semantic_key="run.dev",
                assertion="Run the dev server",
                value="make build",
                confidence="high",
            ),
        ],
    )
    green = AgentClaimSet(
        agent_id="agent_green",
        perspective="code_implementation",
        claims=[
            AgentClaim(
                agent_id="agent_green",
                claim_type="config",
                semantic_key="network.port",
                assertion="The app binds to port 8080 per config.yaml",
                value="8080",
                confidence="high",
                evidence_refs=["config.yaml"],
            ),
            AgentClaim(
                agent_id="agent_green",
                claim_type="workflow",
                semantic_key="run.dev",
                assertion="Run the dev server",
                value="make test",
                confidence="inferred",
            ),
        ],
    )
    return [red, green]


def _layer_from_rid(review_item_id: str) -> str:
    """Derive the semantic layer label from a review_item_id's ``<layer>:`` prefix."""
    return review_item_id.split(":", 1)[0]


def _verdict_for(item, status: str = "passed") -> SemanticAuditVerdict:
    """A single verdict for a ReviewItem (or check carrying a review_item_id)."""
    review_item_id = item.review_item_id
    # The layer is the review_item_id's OWN '<layer>:' prefix (authoritative), so
    # it is always consistent whether the item came from the registry or a check.
    layer = _layer_from_rid(review_item_id)
    return SemanticAuditVerdict(
        review_item_id=review_item_id,
        layer=layer,
        status=status,
        rationale_summary="Auditor upholds this semantic item",
        evidence_refs=["config.yaml"],
        confidence="high",
    )


def _bundle_for_items(
    doc_paths: list[Path],
    items,
    status: str = "passed",
) -> SemanticAuditBundle:
    """A document-fresh audit bundle adjudicating exactly ``items``.

    ``items`` may be ReportReviewItems (from a report's ``review_items``) or
    LayerReport checks carrying a ``review_item_id``. The documents_digest is
    bound to the real (current) writer markdown so the bundle is not stale.
    """
    return SemanticAuditBundle(
        documents_digest=compute_documents_digest(doc_paths),
        auditor="fake_llm_auditor",
        verdicts=[_verdict_for(item, status=status) for item in items],
    )


def _pending_semantic_checks(report) -> list[VerificationCheck]:
    """L3/L4b/L5 layer checks that are still pending and carry a review_item_id."""
    out: list[VerificationCheck] = []
    for layer_name, lr in report.layers.items():
        if layer_name not in ("L3", "L4", "L5"):
            continue
        for check in lr.checks:
            if check.review_item_id and check.status == "pending":
                out.append(check)
    return out


def _check_by_rid(report, review_item_id: str):
    for layer_name, lr in report.layers.items():
        if layer_name not in ("L3", "L4", "L5"):
            continue
        for check in lr.checks:
            if check.review_item_id == review_item_id:
                return check
    return None


# ---------------------------------------------------------------------------
# Test 1: the full authoritative handoff yields a clean PASS
# ---------------------------------------------------------------------------


def test_authoritative_handoff_full_chain_gates_passed(tmp_path: Path) -> None:
    """Repository -> evidence -> scout bundle -> ReBattle -> Judge -> model ->
    writer markdown -> L0-L5 -> audit -> Quality Gate reports ``passed``."""
    proj = _make_project(tmp_path)

    # 1. Python evidence scanner -> EvidenceFacts / MechanicalAssertions
    data, registry = _engineer_evidence(proj)
    detection = data["detection"]
    mechanical = build_claims_from_evidence(detection, registry)
    assert len(mechanical.claims) > 0
    assert all(c.provenance == "python_fact" for c in mechanical.claims)

    # 2. Fake LLM scouts -> AgentClaimBundle, and the real ReBattle organizer
    sets = _scout_claim_sets()
    discrepancies = ReBattleArena.detect_discrepancies(sets)
    topics = {d.topic for d in discrepancies}
    assert "network.port" in topics  # the port conflict is surfaced

    # 3. Fake Judge rulings -> AdjudicatedClaims -> authoritative SemanticModel
    adjudications = [
        AdjudicationResult(
            discrepancy_topic="network.port", ruling="accepted",
            final_assertion="8080",
            adjudicator_reasoning="config.yaml hard-codes 8080",
            verified_via_codebase=True,
        ),
        AdjudicationResult(
            discrepancy_topic="run.dev", ruling="accepted",
            final_assertion="make build",
            adjudicator_reasoning="build target matches Makefile",
            verified_via_codebase=True,
        ),
    ]
    consensus = ReBattleArena.synthesize_consensus(sets, adjudications)
    adjudicated = [c for c in consensus if c.__class__.__name__ == "AdjudicatedClaim"]
    model = SemanticModel()
    fold_adjudicated_into_semantic_model(adjudicated, model)
    assert any(t.title == "run.dev" for t in model.user_tasks)
    assert model.provenance.user_tasks == "llm"

    # 4. Fake LLM-writer markdown + real L0-L5 mechanical verification. Probe
    # with an empty-verdict bundle so Python computes the authoritative registry
    # of pending semantic review items (real, stable review_item_ids).
    writer, docs = _writer_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj, registry=registry)
    probe = SemanticAuditBundle(documents_digest="x", verdicts=[])
    report = orchestrator.verify_documents(
        docs, wiki_dir=writer, semantic_bundle=probe
    )

    # Before an audit, the semantic layers must be pending (honest gap) and the
    # registry of expected review items is non-empty with all items pending.
    for layer in ("L3", "L4", "L5"):
        assert report.layers[layer].verdict == "pending"
    assert report.review_items
    assert all(item.status == "pending" for item in report.review_items)
    # mechanical layers are clean (L4a passes: all technical blocks are tagged)
    assert report.layers["L0"].verdict == "passed"
    assert report.layers["L1"].verdict == "passed"
    assert report.layers["L2"].verdict == "passed"
    assert not [
        c for c in report.layers["L4"].checks
        if c.claim_type == "l4a_mechanical" and c.status == "failed"
    ]

    # 5. Fake LLM Auditor bundle adjudicating EXACTLY the computed review items,
    # folded in by the REAL orchestrator merge, then the real Quality Gate.
    doc_paths = _writer_paths(writer)
    bundle = _bundle_for_items(doc_paths, report.review_items, status="passed")
    assert bundle_matches_documents(bundle, doc_paths) is True  # document-fresh
    report2 = orchestrator.verify_documents(
        docs, wiki_dir=writer, semantic_bundle=bundle
    )

    # Every expected item's check is now adjudicated (passed).
    for item in report.review_items:
        check = _check_by_rid(report2, item.review_item_id)
        assert check is not None and check.status == "passed"
    assert report2.layers["L3"].verdict == "passed"
    assert report2.layers["L4"].verdict == "passed"
    assert report2.layers["L5"].verdict == "passed"

    result = evaluate_quality_gate(report2)
    assert result.verdict == "passed"
    assert result.semantic_complete is True
    assert result.pending_llm_layers == []
    assert result.mechanical_passed is True
    assert result.passed is True
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Test 2: honesty — a stale or absent audit never yields a vacuous pass
# ---------------------------------------------------------------------------


def test_authoritative_handoff_stale_audit_never_passes(tmp_path: Path) -> None:
    """A bundle whose digest no longer matches the (modified) markdown must NOT
    drive the gate to ``passed``. The document-digest staleness guard rejects the
    bundle (the reviewer hands the orchestrator an empty bundle), so L3/L4b/L5
    stay pending and the gate never reports a vacuous pass."""
    proj = _make_project(tmp_path)
    writer, docs = _writer_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)

    doc_paths = _writer_paths(writer)
    probe = SemanticAuditBundle(documents_digest="x", verdicts=[])
    report = orchestrator.verify_documents(docs, wiki_dir=writer, semantic_bundle=probe)
    bundle = _bundle_for_items(doc_paths, report.review_items, status="passed")
    assert bundle_matches_documents(bundle, doc_paths) is True  # fresh now

    # Modify the writer markdown AFTER the bundle was audited -> stale.
    modified = _EN_BODY + "\n\n## Changelog\n\nAdded a new feature.\n"
    (writer / "README.md").write_text(modified, encoding="utf-8")
    doc_paths_now = _writer_paths(writer)
    assert bundle_matches_documents(bundle, doc_paths_now) is False  # stale

    # The document-digest staleness guard drops the bundle (what the CLI does
    # before the merge seam); the real orchestrator receives an EMPTY bundle, so
    # the semantic layers never get adjudicated.
    dropped = SemanticAuditBundle(documents_digest="x", verdicts=[])
    report_stale = orchestrator.verify_documents(
        docs, wiki_dir=writer, semantic_bundle=dropped
    )
    gate = evaluate_quality_gate(report_stale)
    # Never a vacuous pass: verdict is pending/failed, never "passed".
    assert gate.verdict != "passed"
    assert gate.semantic_complete is False
    assert set(gate.pending_llm_layers) >= {"L3", "L5"}


def test_authoritative_handoff_absent_audit_never_passes(tmp_path: Path) -> None:
    """With NO audit bundle, the semantic layers stay pending and the gate never
    reports a clean PASS."""
    proj = _make_project(tmp_path)
    writer, docs = _writer_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)
    report = orchestrator.verify_documents(docs, wiki_dir=writer)

    gate = evaluate_quality_gate(report)
    assert gate.verdict == "pending_semantic_review"
    assert gate.verdict != "passed"
    assert gate.semantic_complete is False
    assert "L3" in gate.pending_llm_layers


def test_authoritative_handoff_partial_then_full_audit(tmp_path: Path) -> None:
    """The prescribed partial->full progression: a partial bundle must NOT flip
    the whole semantic layers (unmentioned items stay pending; gate stays
    pending_semantic_review); a follow-up bundle that adjudicates the remaining
    still-pending items drives the gate to a clean pass (item-level merge)."""
    proj = _make_project(tmp_path)
    writer, docs = _writer_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)
    doc_paths = _writer_paths(writer)

    # 1. Mechanical verify -> the authoritative registry (>=3 items across L3/L4b/L5).
    probe = SemanticAuditBundle(documents_digest="x", verdicts=[])
    report = orchestrator.verify_documents(docs, wiki_dir=writer, semantic_bundle=probe)
    assert report.layers["L3"].verdict == "pending"
    assert report.layers["L4"].verdict == "pending"
    assert report.layers["L5"].verdict == "pending"
    items = list(report.review_items)
    assert len(items) >= 3
    l3_items = [i for i in items if i.layer == "L3"]
    l4b_items = [i for i in items if i.layer == "L4b"]
    l5_items = [i for i in items if i.layer == "L5"]
    assert l3_items and l4b_items and l5_items

    # 2. PARTIAL: adjudicate only ONE item (the first L3 item) as passed.
    partial = _bundle_for_items(doc_paths, [l3_items[0]], status="passed")
    report_partial = orchestrator.verify_documents(
        docs, wiki_dir=writer, semantic_bundle=partial
    )
    # L3 (only one item) resolves; L4b/L5 keep unmentioned items -> still pending.
    assert report_partial.layers["L3"].verdict == "passed"
    assert report_partial.layers["L4"].verdict == "pending"
    assert report_partial.layers["L5"].verdict == "pending"
    # The unmentioned L4b/L5 items remain pending (item-level, not whole-layer).
    for item in l4b_items + l5_items:
        assert _check_by_rid(report_partial, item.review_item_id).status == "pending"
    gate_partial = evaluate_quality_gate(report_partial)
    assert gate_partial.verdict == "pending_semantic_review"
    assert gate_partial.passed is False
    assert gate_partial.semantic_complete is False
    # EXIT-CODE SEPARATION: the CI exit code must be decoupled from the truth
    # verdict. The real gate maps a pending_semantic_review to ci_exit_code 0 by
    # default (an LLM review outstanding is not a mechanical failure), so exit 0
    # here means "semantic review pending, allowed by exit policy" — NOT passed.
    # Asserting this pinpoints that a genuine pending is honored (never
    # short-circuited into a vacuous pass just because the exit code is 0).
    assert gate_partial.ci_exit_code == 0
    assert gate_partial.exit_code == gate_partial.ci_exit_code  # alias stays honest
    assert gate_partial.passed is False  # exit-0 is never conflated with passed
    # The CLAUDE.md "0-or-2" exit policy: the SAME pending_semantic_review
    # verdict maps to the honest base code 2 when allow_pending_llm_layers is not
    # granted — the verdict-to-code mapping, pinned directly from the gate's own
    # policy table.
    assert ci_exit_code_for("pending_semantic_review", allow_pending_llm_layers=False) == 2
    assert ci_exit_code_for("pending_semantic_review", allow_pending_llm_layers=True) == 0
    # And under the strict policy the real gate keeps the HONEST verdict — the
    # unadjudicated bundle stays PENDING_SEMANTIC_REVIEW (never papered over as a
    # pass, never escalated to failed) — but exits at the honest base code 2
    # because the exit policy was not granted. ``allow_pending_llm_layers`` is
    # EXIT POLICY ONLY: it can never turn a pending semantic item into a failure.
    gate_partial_strict = evaluate_quality_gate(
        report_partial, allow_pending_llm_layers=False
    )
    assert gate_partial_strict.verdict == "pending_semantic_review"
    assert gate_partial_strict.ci_exit_code == 2
    assert gate_partial_strict.passed is False

    # 3. FULL: build from the review-item registry of the partial report. The
    # registry still lists every expected item (the L3 item included), so this
    # is a complete bundle; re-adjudicating the already-passed L3 item is
    # idempotent, and the still-unadjudicated L4b/L5 items now resolve too.
    # (verify_documents is stateless, so the full bundle must cover every item
    # a fresh report would leave pending.)
    still_pending = _pending_semantic_checks(report_partial)
    assert still_pending, "expected remaining pending semantic items"
    full = _bundle_for_items(doc_paths, report_partial.review_items, status="passed")
    report_full = orchestrator.verify_documents(
        docs, wiki_dir=writer, semantic_bundle=full
    )
    gate_full = evaluate_quality_gate(report_full)
    assert gate_full.verdict == "passed"
    assert gate_full.passed is True
    assert gate_full.semantic_complete is True
    assert gate_full.pending_llm_layers == []
    assert gate_full.ci_exit_code == 0
    # The full verdict-to-code closure of the CLAUDE.md exit-policy table.
    assert ci_exit_code_for("passed") == 0
    assert ci_exit_code_for("failed") == 1
    assert ci_exit_code_for("pending_mechanical_verification") == 3


# ---------------------------------------------------------------------------
# Test 3: an untagged technical block is a mechanical L4a failure
# ---------------------------------------------------------------------------


def test_authoritative_handoff_untagged_technical_block_fails_l4a(
    tmp_path: Path,
) -> None:
    """An LLM-writer bash block WITHOUT a ``[[id:...]]`` marker cannot participate
    in stable-ID parity, so the mechanical L4a layer contains a FAILED
    ``l4a_mechanical`` check. Tagged writers must not regress this."""
    proj = _make_project(tmp_path)

    # The untagged technical block: a bash fence with no [[id:...]] marker.
    untagged_en = """# myapp

myapp is a tiny scaffold.

## Build

```bash
make build
```
"""
    writer, docs = _writer_docs(tmp_path, en_body=untagged_en, zh_body=untagged_en)

    orchestrator = VerificationOrchestrator(proj)
    report = orchestrator.verify_documents(docs, wiki_dir=writer)

    l4a = [c for c in report.layers["L4"].checks if c.claim_type == "l4a_mechanical"]
    untagged_failures = [
        c for c in l4a
        if c.status == "failed" and "Untagged technical code block" in c.claim_text
    ]
    assert len(untagged_failures) > 0, "expected failed untagged-block L4a check"
    for c in untagged_failures:
        assert c.status == "failed"
        assert c.verified is False

    # The gate must not report a clean pass over a mechanical parity failure.
    gate = evaluate_quality_gate(report)
    assert gate.verdict == "failed"
    assert gate.passed is False


def test_authoritative_handoff_makewiki_config_imported() -> None:
    """Sanity: the fixture uses the real config module (guards a broken import)."""
    assert hasattr(config_mod, "MakeWikiConfig")
