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
from makewiki_skills.verification.quality_gate import evaluate_quality_gate
from makewiki_skills.verification.report import LayerReport, VerificationCheck
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

## Build

[[id:build]]
```bash
make build
```

## Test

[[id:test]]
```bash
make test
```

## Run

[[id:run]]
```bash
myapp run --port 8080
```

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


def fold_semantic_bundle(
    report: object,
    bundle: SemanticAuditBundle | None,
    doc_paths: list[Path],
) -> bool:
    """Python-side validate+aggregate of the LLM Auditor's SemanticAuditBundle.

    This is the mechanical half of the audit handoff: Python checks the bundle's
    ``documents_digest`` actually matches the current writer markdown and, only
    then, folds the Auditor's *semantic* verdicts (L3 behavior, L4b prose parity,
    L5 epistemic) into the corresponding report layers. Mechanical L4a checks are
    preserved untouched — a bundle can never paper over a mechanical failure.

    Returns ``False`` (leaving the semantic layers ``pending``) when the bundle
    is absent or stale, so the gate can never report a vacuous ``passed``.
    """
    if bundle is None:
        return False
    if not bundle_matches_documents(bundle, doc_paths):
        return False

    layer_map: dict[str, str] = {"L3": "L3", "L4b": "L4", "L5": "L5"}
    by_layer: dict[str, list[SemanticAuditVerdict]] = {}
    for verdict in bundle.verdicts:
        by_layer.setdefault(layer_map[verdict.layer], []).append(verdict)

    for layer, verdicts in by_layer.items():
        passed_checks = [
            VerificationCheck(
                layer=layer,
                target=v.review_item_id,
                language_code="|".join(v.evidence_refs) or "all",
                claim_type=v.layer,
                claim_text=v.rationale_summary,
                verified=True,
                status="passed",
                verification_source="llm_audit",
                detail=v.rationale_summary,
            )
            for v in verdicts
        ]
        if layer == "L4":
            # Keep the mechanical L4a checks; replace only the reserved L4b
            # semantic check with the Auditor's passed verdict(s).
            kept = [c for c in report.layers[layer].checks if c.claim_type != "l4b_semantic"]
            report.layers[layer] = LayerReport(
                layer=layer, name="Cross-Language", checks=kept + passed_checks
            )
        else:
            report.layers[layer] = LayerReport(
                layer=layer, name=layer, checks=passed_checks
            )
    return True


def _fresh_audit_bundle(doc_paths: list[Path]) -> SemanticAuditBundle:
    digest = compute_documents_digest(doc_paths)
    return SemanticAuditBundle(
        documents_digest=digest,
        auditor="fake_llm_auditor",
        verdicts=[
            SemanticAuditVerdict(
                review_item_id="L3:workflow.run", layer="L3", status="passed",
                rationale_summary="run workflow verified against Makefile",
                evidence_refs=["Makefile"],
            ),
            SemanticAuditVerdict(
                review_item_id="L4b:semantic-parity", layer="L4b", status="passed",
                rationale_summary="prose parity consistent across EN and zh-CN",
                evidence_refs=["README.md", "README.zh-CN.md"],
            ),
            SemanticAuditVerdict(
                review_item_id="L5:epistemic", layer="L5", status="passed",
                rationale_summary="assertions match mechanical evidence confidence",
                evidence_refs=["config.yaml"],
            ),
        ],
    )


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

    # 4. Fake LLM-writer markdown + real L0-L5 mechanical verification
    writer, docs = _writer_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj, registry=registry)
    report = orchestrator.verify_documents(docs, wiki_dir=writer)

    # Before an audit, the semantic layers must be pending (honest gap).
    for layer in ("L3", "L4", "L5"):
        assert report.layers[layer].verdict == "pending"
    # mechanical layers are clean (L4a passes: all technical blocks are tagged)
    assert report.layers["L0"].verdict == "passed"
    assert report.layers["L1"].verdict == "passed"
    assert report.layers["L2"].verdict == "passed"
    assert not [
        c for c in report.layers["L4"].checks
        if c.claim_type == "l4a_mechanical" and c.status == "failed"
    ]

    # 5. Fake LLM Auditor bundle + Python validate/aggregate + Quality Gate
    doc_paths = _writer_paths(writer)
    bundle = _fresh_audit_bundle(doc_paths)
    assert fold_semantic_bundle(report, bundle, doc_paths) is True

    result = evaluate_quality_gate(report)
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
    drive the gate to ``passed`` — the semantic layers stay ``pending``."""
    proj = _make_project(tmp_path)
    writer, docs = _writer_docs(tmp_path)
    orchestrator = VerificationOrchestrator(proj)
    report = orchestrator.verify_documents(docs, wiki_dir=writer)

    doc_paths = _writer_paths(writer)
    bundle = _fresh_audit_bundle(doc_paths)
    assert bundle_matches_documents(bundle, doc_paths) is True  # fresh now

    # Modify the writer markdown AFTER the bundle was audited -> stale.
    modified = _EN_BODY + "\n\n## Changelog\n\nAdded a new feature.\n"
    (writer / "README.md").write_text(modified, encoding="utf-8")
    doc_paths_now = _writer_paths(writer)
    assert bundle_matches_documents(bundle, doc_paths_now) is False  # stale

    assert fold_semantic_bundle(report, bundle, doc_paths_now) is False
    gate = evaluate_quality_gate(report)
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

    doc_paths = _writer_paths(writer)
    assert fold_semantic_bundle(report, None, doc_paths) is False

    gate = evaluate_quality_gate(report)
    assert gate.verdict == "pending_semantic_review"
    assert gate.verdict != "passed"
    assert gate.semantic_complete is False
    assert "L3" in gate.pending_llm_layers


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
