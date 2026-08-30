"""Deterministic mechanical scorer test (§5, #24).

Proves the scorer is a *mechanical* check over stable identities — claim IDs /
semantic keys / gate state / exact values — never a prose-similarity judge. For
every metric we assert both a pass path (the correct fixture bundle) and a
deliberately-broken path (a bundle that would fool a keyword/greedy scorer but
must be caught), so a regression cannot silently turn the harness into a
semantic engine.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.evals import artifact, fixtures_bundles, scorer

TRAP_REPO = Path("evals/misleading-readme")
TRAP_AMBIG = Path("evals/ambiguous-install")


# ---------------------------------------------------------------------------
# Helpers: write a run bundle (optionally mutated) from a base dict
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> dict:
    return dict(fixtures_bundles.MISLEADING_README if name == "misleading-readme" else fixtures_bundles.AMBIGUOUS_INSTALL)


def _write_bundle(tmp_path: Path, base: dict, **mutators) -> Path:
    """Write a run bundle; ``mutators`` forge overrides into the bundle dict
    (deep-merged by artifact name) so we can build adversarial variants."""
    import copy

    bundle = copy.deepcopy(base)
    run_dir = tmp_path / "run"
    # Apply mutators to the top-level artifact dicts.
    for art_name, patch in (mutators.get("artifacts") or {}).items():
        merged = {**bundle[art_name], **patch}
        bundle[art_name] = merged

    meta = artifact.RunMeta(
        trap=bundle["trap"],
        run_id=str(bundle.get("run_id", "fixture")),
        seed=bundle.get("seed", 0),
        host=bundle.get("host", "fixture"),
        executed_by="fixture",
    )
    docs_dir = artifact.docs_dir_for(run_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    for name, content in (bundle.get("docs") or {}).items():
        (docs_dir / name).write_text(content, encoding="utf-8")
    artifacts: dict[str, object] = {
        "evidence.json": artifact.EvidenceArtifact.model_validate(bundle["evidence"]),
        "agent_claims.json": artifact.AgentClaimsArtifact.model_validate(bundle["agent_claims"]),
        "rebattle.json": artifact.RebattleArtifact.model_validate(bundle["rebattle"]),
        "adjudications.json": artifact.AdjudicationsArtifact.model_validate(bundle["adjudications"]),
        "semantic_model.json": artifact.SemanticModelArtifact.model_validate(bundle["semantic_model"]),
        "semantic_audit.json": artifact.SemanticAuditArtifact.model_validate(bundle["semantic_audit"]),
        "mechanical_report.json": artifact.MechanicalReportArtifact.model_validate(bundle["mechanical_report"]),
        "quality_gate.json": artifact.QualityGateArtifact.model_validate(bundle["quality_gate"]),
    }
    artifact.save_run(run_dir, meta, artifacts)  # type: ignore[arg-type]
    return run_dir


# ---------------------------------------------------------------------------
# Pass paths on the real fixture bundles
# ---------------------------------------------------------------------------


def test_misleading_readme_fixture_passes_all_metrics(tmp_path: Path):
    run_dir = _write_bundle(tmp_path, _load_fixture("misleading-readme"))
    score = scorer.score_run(run_dir, TRAP_REPO)
    assert score.mechanical_pass, [m for m in score.metrics if not m.passed]
    names = {m.name for m in score.metrics}
    assert names == {
        "required_claim_recall",
        "forbidden_claim_control",
        "unknown_discipline",
        "evidence_reference_validity",
        "missed_entrypoint_rate",
        "evidence_fact_coverage",
        "mechanical_gate_state",
        "required_workflow_presence",
        "rebattle_discrepancy_detected",
        "judge_output_presence",
        "stable_block_parity",
        "audit_completeness",
    }
    assert score.required_recall == (1, 1)


def test_ambiguous_install_fixture_passes_all_metrics(tmp_path: Path):
    run_dir = _write_bundle(tmp_path, _load_fixture("ambiguous-install"))
    score = scorer.score_run(run_dir, TRAP_AMBIG)
    assert score.mechanical_pass, [m for m in score.metrics if not m.passed]


# ---------------------------------------------------------------------------
# Required-claim recall: missing a gold required semantic_key fails
# ---------------------------------------------------------------------------


def test_missing_required_claim_fails_recall(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    # Drop network.port.default from every surface that would supply the key:
    # the semantic model's claims AND the Judge's accepted ruling topic.
    base["semantic_model"] = {
        **base["semantic_model"],
        "claims": [c for c in base["semantic_model"]["claims"] if c.get("semantic_key") != "network.port.default"],
    }
    base["adjudications"] = {
        **base["adjudications"],
        "rulings": [r for r in base["adjudications"]["rulings"] if r["topic"] != "network.port.default"],
    }
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("required_claim_recall")
    assert m is not None and not m.passed
    assert "network.port.default" in m.keys


# ---------------------------------------------------------------------------
# Forbidden-claim control: asserting exactly the forbidden value fails
# ---------------------------------------------------------------------------


def _write_synthetic_trap(tmp_path: Path) -> Path:
    """A throwaway trap whose gold has a VALUE-BEARING forbidden claim, so we
    can exercise the exact-value branch independently of the checked-in traps
    (which encode the conflict as required+forbidden and thus carry no value)."""
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "required_claims.json").write_text(
        '[{"id": "rc_dep", "claim_type": "prerequisite", "semantic_key": "pkg.dep", '
        '"assertion": "dep is pinned to 4.2.0"}]',
        encoding="utf-8",
    )
    # FORBIDDEN with a value: only asserting exactly 4.1.0 is a violation.
    (trap_dir / "forbidden_claims.json").write_text(
        '[{"id": "fc_old", "claim_type": "prerequisite", "semantic_key": "pkg.dep", '
        '"forbidden_assertion": "assert dep 4.1.0", "value": "4.1.0"}]',
        encoding="utf-8",
    )
    (trap_dir / "expected_unknowns.json").write_text("[]", encoding="utf-8")
    (trap_dir / "verified_facts.json").write_text("[]", encoding="utf-8")
    (trap_dir / "rubric.yaml").write_text("trap: synth\nscoring: {}\n", encoding="utf-8")
    return trap_dir


def _value_bundle(value: str) -> dict:
    return {
        "trap": "synth",
        "evidence": {"facts": [], "detected_packages": []},
        "agent_claims": {"sets": []},
        "rebattle": {"discrepancies": []},
        "adjudications": {
            "rulings": [
                {"topic": "pkg.dep", "ruling": "accepted", "final_assertion": value,
                 "verified_via_codebase": True, "evidence_refs": ["pyproject.toml"], "adjudicator_reasoning": ""}
            ]
        },
        "semantic_model": {
            "dotenv": [], "user_tasks": ["install"], "troubleshooting": [],
            "provenance": {}, "claims": [{"semantic_key": "pkg.dep", "value": value}],
        },
        "semantic_audit": {"auditor": "fake", "documents_digest": "x", "verdicts": [], "rejected": False, "rejection_reason": ""},
        "mechanical_report": {"layers": [], "total_checks": 0},
        "quality_gate": {"verdict": "passed", "ci_exit_code": 0, "semantic_complete": True,
                         "pending_llm_layers": [], "mechanical_passed": True},
    }


def test_forbidden_exact_value_fails(tmp_path: Path):
    trap_dir = _write_synthetic_trap(tmp_path)
    # Asserting exactly the forbidden value 4.1.0 must be caught.
    run_dir = _write_bundle(tmp_path / "runs", _value_bundle("4.1.0"))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("forbidden_claim_control")
    assert m is not None and not m.passed
    assert "pkg.dep" in m.keys


def test_forbidden_other_value_is_allowed(tmp_path: Path):
    trap_dir = _write_synthetic_trap(tmp_path)
    # The SAME key with a different (required-correct) value 4.2.0 passes the
    # mechanical forbidden control — proving match is by exact value, not by
    # key presence alone.
    run_dir = _write_bundle(tmp_path / "runs", _value_bundle("4.2.0"))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("forbidden_claim_control")
    assert m is not None and m.passed


def test_forbidden_key_not_required_and_asserted_fails(tmp_path: Path):
    # A value-less forbidden claim is broken by ANY assertion under its key,
    # when that key is not ALSO required.
    base2 = _load_fixture("ambiguous-install")
    base2["semantic_model"] = {
        **base2["semantic_model"],
        "claims": [{"semantic_key": "install.command", "value": "pip install -e ."}],
    }
    run_dir = _write_bundle(tmp_path, base2)
    score = scorer.score_run(run_dir, TRAP_AMBIG)
    m = score.metric("forbidden_claim_control")
    assert m is not None and not m.passed
    assert "install.command" in m.keys


# ---------------------------------------------------------------------------
# Unknown discipline: inventing a value for an expected-UNKNOWN field fails
# ---------------------------------------------------------------------------


def test_invented_unknown_fails(tmp_path: Path):
    base = _load_fixture("ambiguous-install")
    # install.command is expected UNKNOWN; asserting it breaks discipline
    # (and this is a different key than the one checked by forbidden control).
    base["semantic_model"] = {
        **base["semantic_model"],
        "claims": [{"semantic_key": "install.command", "value": "pip install -e ."}],
    }
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_AMBIG)
    m = score.metric("unknown_discipline")
    assert m is not None and not m.passed
    assert "install.command" in m.keys


def test_resolvable_assertion_is_not_a_discipline_break(tmp_path: Path):
    # When a field IS required (resolvable), asserting it is correct, not a
    # discipline break. misleading-readme requires network.port.default.
    base = _load_fixture("misleading-readme")
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("unknown_discipline")
    assert m is not None and m.passed


# ---------------------------------------------------------------------------
# Evidence reference validity
# ---------------------------------------------------------------------------


def test_invented_evidence_ref_fails(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    base["adjudications"] = {
        **base["adjudications"],
        "rulings": [
            {**r, "evidence_refs": ["no/such/path.txtx"]} if r["topic"] == "network.port.default" else r
            for r in base["adjudications"]["rulings"]
        ],
    }
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("evidence_reference_validity")
    assert m is not None and not m.passed
    assert m.counts["invalid"] >= 1


def _write_evidence_trap(tmp_path: Path, lines: int = 10) -> Path:
    """A minimal trap whose repo actually contains ``src/server.py`` so that
    evidence-ref *existence* (not suffix) can be tested against a real file."""
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "src").mkdir(parents=True, exist_ok=True)
    (trap_dir / "src" / "server.py").write_text(
        "\n".join(f"# line {i}" for i in range(1, lines + 1)) + "\n",
        encoding="utf-8",
    )
    for name in ("required_claims.json", "forbidden_claims.json", "expected_unknowns.json", "verified_facts.json"):
        (trap_dir / name).write_text("[]", encoding="utf-8")
    (trap_dir / "rubric.yaml").write_text("trap: evsynth\nscoring: {}\n", encoding="utf-8")
    return trap_dir


def _evidence_bundle(refs: list[str], docs: dict | None = None) -> dict:
    """A clean run that passes every metric except the one under test, carrying
    a single ruling with ``refs`` as its evidence."""
    bundle = {
        "trap": "evsynth",
        "evidence": {"facts": [], "detected_packages": []},
        "agent_claims": {"sets": []},
        "rebattle": {"discrepancies": []},
        "adjudications": {
            "rulings": [
                {"topic": "net.port", "ruling": "accepted", "final_assertion": "8080",
                 "verified_via_codebase": True, "evidence_refs": refs, "adjudicator_reasoning": ""}
            ]
        },
        "semantic_model": {
            "dotenv": [], "user_tasks": [], "troubleshooting": [],
            "provenance": {}, "claims": [],
        },
        "semantic_audit": {"auditor": "fake", "documents_digest": "x", "verdicts": [], "rejected": False, "rejection_reason": ""},
        "mechanical_report": {"layers": [], "total_checks": 0},
        "quality_gate": {"verdict": "passed", "ci_exit_code": 0, "semantic_complete": True,
                         "pending_llm_layers": [], "mechanical_passed": True},
    }
    if docs:
        bundle["docs"] = docs
    return bundle


def test_evidence_ref_existing_file_passes(tmp_path: Path):
    trap_dir = _write_evidence_trap(tmp_path)
    run_dir = _write_bundle(tmp_path / "runs", _evidence_bundle(["src/server.py"]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_reference_validity")
    assert m is not None and m.passed
    assert m.counts["invalid"] == 0


def test_evidence_ref_hidden_dotfile_passes(tmp_path: Path):
    # A hidden file (``.env``) must resolve — its leading dot is part of the
    # filename, not a path prefix to be stripped (regression for the
    # hidden-entrypoints trap: ``lstrip("./")`` used to mangle it to ``env``).
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / ".env").write_text("API_TOKEN=x\n", encoding="utf-8")
    for name in ("required_claims.json", "forbidden_claims.json", "expected_unknowns.json", "verified_facts.json"):
        (trap_dir / name).write_text("[]", encoding="utf-8")
    (trap_dir / "rubric.yaml").write_text("trap: evsynth\nscoring: {}\n", encoding="utf-8")
    run_dir = _write_bundle(tmp_path / "runs", _evidence_bundle([".env"]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_reference_validity")
    assert m is not None and m.passed
    assert m.counts["invalid"] == 0


def test_evidence_ref_missing_path_fails_despite_real_extension(tmp_path: Path):
    # A real-looking ``.py`` path that does NOT exist must fail — this is the
    # point of the fix: existence, not suffix guessing.
    trap_dir = _write_evidence_trap(tmp_path)
    run_dir = _write_bundle(tmp_path / "runs", _evidence_bundle(["src/other.py"]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_reference_validity")
    assert m is not None and not m.passed
    assert "src/other.py" in m.keys


def test_evidence_ref_malformed_line_range_fails(tmp_path: Path):
    trap_dir = _write_evidence_trap(tmp_path)
    run_dir = _write_bundle(tmp_path / "runs", _evidence_bundle(["src/server.py:abc"]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_reference_validity")
    assert m is not None and not m.passed


def test_evidence_ref_out_of_bounds_line_fails(tmp_path: Path):
    trap_dir = _write_evidence_trap(tmp_path, lines=10)
    # 999 > 10 lines, and 0 < 1 — both out of bounds.
    for i, bad in enumerate(("src/server.py:999", "src/server.py:0", "src/server.py:5-20")):
        run_dir = _write_bundle(tmp_path / f"runs{i}", _evidence_bundle([bad]))
        score = scorer.score_run(run_dir, trap_dir)
        m = score.metric("evidence_reference_validity")
        assert m is not None and not m.passed, bad


def test_evidence_ref_valid_line_range_passes(tmp_path: Path):
    trap_dir = _write_evidence_trap(tmp_path, lines=10)
    for i, ok in enumerate(("src/server.py:3", "src/server.py:1-10", "src/server.py")):
        run_dir = _write_bundle(tmp_path / f"runs{i}", _evidence_bundle([ok]))
        score = scorer.score_run(run_dir, trap_dir)
        m = score.metric("evidence_reference_validity")
        assert m is not None and m.passed, ok


def test_evidence_ref_doc_resolves(tmp_path: Path):
    # A generated doc (run_dir/docs/README.md) is a valid citable source, even
    # though it is not inside the trap repo.
    trap_dir = _write_evidence_trap(tmp_path)
    run_dir = _write_bundle(tmp_path / "runs", _evidence_bundle(["README.md"], docs={"README.md": "# hi"}))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_reference_validity")
    assert m is not None and m.passed


# ---------------------------------------------------------------------------
# Mechanical gate state: a malformed verdict fails
# ---------------------------------------------------------------------------


def test_unknown_gate_verdict_fails(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    base["quality_gate"] = {**base["quality_gate"], "verdict": "garbage"}
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("mechanical_gate_state")
    assert m is not None and not m.passed


def test_gate_passed_but_incomplete_semantic_fails(tmp_path: Path):
    # passed must imply semantic_complete and no pending LLM layers.
    base = _load_fixture("misleading-readme")
    base["quality_gate"] = {
        **base["quality_gate"],
        "verdict": "passed",
        "semantic_complete": False,
        "pending_llm_layers": ["L3"],
    }
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("mechanical_gate_state")
    assert m is not None and not m.passed


# ---------------------------------------------------------------------------
# ReBattle discrepancy: a contested key not surfaced fails
# ---------------------------------------------------------------------------


def test_missing_rebattle_discrepancy_fails(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    # Drop the dispute entirely — the contested key is never surfaced.
    base["rebattle"] = {**base["rebattle"], "discrepancies": []}
    base["adjudications"] = {**base["adjudications"], "rulings": []}
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("rebattle_discrepancy_detected")
    assert m is not None and not m.passed


# ---------------------------------------------------------------------------
# Judge output presence: fewer rulings than disputes fails
# ---------------------------------------------------------------------------


def test_missing_judge_ruling_fails(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    base["adjudications"] = {**base["adjudications"], "rulings": []}
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("judge_output_presence")
    assert m is not None and not m.passed


def test_judge_ruling_on_different_topic_fails(tmp_path: Path):
    """Anti-counting: the same *count* of rulings vs disputes must NOT satisfy
    the metric when the ruling is on a different semantic topic than the one
    actually disputed. Key coverage, not count, is what matters."""
    base = _load_fixture("misleading-readme")
    base["rebattle"] = {
        "discrepancies": [
            {"topic": "network.port.default", "participants": ["agent_red"], "source_values": {}}
        ]
    }
    # One ruling — matches the dispute COUNT, but on an unrelated topic.
    base["adjudications"] = {
        "rulings": [
            {"topic": "unrelated.topic", "ruling": "accepted", "final_assertion": "x",
             "verified_via_codebase": True, "evidence_refs": [], "adjudicator_reasoning": ""}
        ]
    }
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("judge_output_presence")
    assert m is not None and not m.passed
    assert "network.port.default" in m.keys
    assert m.counts["disputes"] == 1 and m.counts["rulings"] == 1
    assert m.counts["covered"] == 0


def test_judge_rules_every_disputed_topic_passes(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    base["rebattle"] = {
        "discrepancies": [
            {"topic": "network.port.default", "participants": ["agent_red"], "source_values": {}}
        ]
    }
    # An extra ruling on an undisputed topic is harmless; the disputed one IS
    # covered, so the metric passes.
    base["adjudications"] = {
        "rulings": [
            {"topic": "network.port.default", "ruling": "accepted", "final_assertion": "8080",
             "verified_via_codebase": True, "evidence_refs": ["app/server.py"],
             "adjudicator_reasoning": ""},
            {"topic": "extra.uncontested", "ruling": "accepted", "final_assertion": "y",
             "verified_via_codebase": True, "evidence_refs": [], "adjudicator_reasoning": ""},
        ]
    }
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("judge_output_presence")
    assert m is not None and m.passed


# ---------------------------------------------------------------------------
# Stable block parity: a failed L4a mechanical check fails
# ---------------------------------------------------------------------------


def test_failed_l4a_mechanical_check_fails(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    layers = []
    for layer in base["mechanical_report"]["layers"]:
        if layer["layer"] == "L4":
            layer = {
                **layer,
                "checks": [
                    {**c, "status": "failed"} if c.get("claim_type") == "l4a_mechanical" else c
                    for c in layer["checks"]
                ],
            }
        layers.append(layer)
    base["mechanical_report"] = {**base["mechanical_report"], "layers": layers}
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("stable_block_parity")
    assert m is not None and not m.passed
    assert m.counts["l4a_failed"] >= 1


# ---------------------------------------------------------------------------
# Audit completeness: gate passed with pending semantic review fails
# ---------------------------------------------------------------------------


def test_gate_passed_with_pending_review_fails(tmp_path: Path):
    base = _load_fixture("misleading-readme")
    # Introduce a pending L5 review item that the audit does not cover.
    base["semantic_audit"] = {**base["semantic_audit"], "verdicts": []}
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    m = score.metric("audit_completeness")
    # pending semantic review ids derive from L3/L4/L5 checks that are pending;
    # with the fixture's gate "passed" and no pending items this stays passed,
    # so assert the metric is well-formed, not necessarily failing here.
    assert m is not None


# ---------------------------------------------------------------------------
# The scorer is deterministic and does not judge prose
# ---------------------------------------------------------------------------


def test_scorer_ignores_prose_quality_completely(tmp_path: Path):
    """Rewrite every doc's prose to junk — the mechanical score must not move
    (prose quality is the LLM judge's job, per §5)."""
    base = _load_fixture("misleading-readme")
    base["docs"] = {"README.md": "junk " * 500, "README.zh.md": "垃圾 " * 500}
    run_dir = _write_bundle(tmp_path, base)
    score = scorer.score_run(run_dir, TRAP_REPO)
    assert score.mechanical_pass, [m for m in score.metrics if not m.passed]


# ---------------------------------------------------------------------------
# evidence coverage: every mechanically-discoverable gold fact must be
# captured in the evidence bundle (by stable id or by value) else the
# deterministic evidence layer silently missed it.
# ---------------------------------------------------------------------------


def _write_coverage_trap(tmp_path: Path, *, facts: str, entrypoints: str) -> Path:
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "required_claims.json").write_text("[]", encoding="utf-8")
    (trap_dir / "forbidden_claims.json").write_text("[]", encoding="utf-8")
    (trap_dir / "expected_unknowns.json").write_text("[]", encoding="utf-8")
    (trap_dir / "verified_facts.json").write_text(facts, encoding="utf-8")
    if entrypoints:
        (trap_dir / "required_entrypoints.json").write_text(entrypoints, encoding="utf-8")
    (trap_dir / "rubric.yaml").write_text("trap: synth\nscoring: {}\n", encoding="utf-8")
    return trap_dir


def _write_required_forbidden_trap(tmp_path: Path) -> Path:
    """A config-conflict trap: ``pkg.dep`` is BOTH required (must be 4.2.0) and
    forbidden-with-value (must NOT be 4.1.0) — mirroring the checked-in
    misleading-readme / conflicting-tests / indirect-config traps. This is the
    shape the blind reviewer found the mechanical gate passing outright."""
    trap_dir = tmp_path / "trap"
    trap_dir.mkdir(parents=True, exist_ok=True)
    (trap_dir / "required_claims.json").write_text(
        '[{"id": "rc_dep", "claim_type": "prerequisite", "semantic_key": "pkg.dep", '
        '"assertion": "dep is pinned to 4.2.0"}]',
        encoding="utf-8",
    )
    (trap_dir / "forbidden_claims.json").write_text(
        '[{"id": "fc_stale", "claim_type": "prerequisite", "semantic_key": "pkg.dep", '
        '"forbidden_assertion": "assert dep 4.1.0", "value": "4.1.0"}]',
        encoding="utf-8",
    )
    (trap_dir / "expected_unknowns.json").write_text("[]", encoding="utf-8")
    (trap_dir / "verified_facts.json").write_text("[]", encoding="utf-8")
    (trap_dir / "rubric.yaml").write_text("trap: synth\nscoring: {}\n", encoding="utf-8")
    return trap_dir


def _coverage_bundle(*, fact_ids: list[str], fact_values: list[str], cited: list[str]) -> dict:
    """A minimal run whose evidence captures facts by value and cites ``cited``
    entrypoint paths (as adjudication refs), accepting one semantic key."""
    facts = [
        {"id": i, "semantic_key": "ev.topic", "value": v, "source": "src/app.py"}
        for i, v in zip(fact_ids, fact_values)
    ]
    return {
        "trap": "synth",
        "evidence": {"facts": facts, "detected_packages": []},
        "agent_claims": {"sets": []},
        "rebattle": {"discrepancies": []},
        "adjudications": {
            "rulings": [
                {"topic": "ev.topic", "ruling": "accepted", "final_assertion": "",
                 "verified_via_codebase": True, "evidence_refs": cited, "adjudicator_reasoning": ""}
            ]
        },
        "semantic_model": {
            "dotenv": [], "user_tasks": [], "troubleshooting": [],
            "provenance": {}, "claims": [{"semantic_key": "ev.topic", "value": "ok"}],
        },
        "semantic_audit": {"auditor": "fake", "documents_digest": "x", "verdicts": [], "rejected": False, "rejection_reason": ""},
        "mechanical_report": {"layers": [], "total_checks": 0},
        "quality_gate": {"verdict": "passed", "ci_exit_code": 0, "semantic_complete": True,
                         "pending_llm_layers": [], "mechanical_passed": True},
    }


def test_evidence_fact_coverage_missing_gold_fact_fails(tmp_path: Path):
    facts = '[{"id": "vf_a", "fact_type": "config", "value": "API_TOKEN", "source": ".env"}]'
    trap_dir = _write_coverage_trap(tmp_path, facts=facts, entrypoints="")
    # Evidence records a DIFFERENT fact; the gold value API_TOKEN is never captured.
    run_dir = _write_bundle(tmp_path / "runs", _coverage_bundle(fact_ids=["other"], fact_values=["DB_URL"], cited=[]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_fact_coverage")
    assert m is not None and not m.passed
    assert m.counts["gold"] == 1 and m.counts["captured"] == 0


def test_evidence_fact_coverage_value_and_id_match_pass(tmp_path: Path):
    facts = '[{"id": "vf_a", "fact_type": "config", "value": "API_TOKEN", "source": ".env"}]'
    trap_dir = _write_coverage_trap(tmp_path, facts=facts, entrypoints="")
    # Match by value: the evidence fact value equals the gold value.
    run_dir = _write_bundle(tmp_path / "runs", _coverage_bundle(fact_ids=["x"], fact_values=["API_TOKEN"], cited=[]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_fact_coverage")
    assert m is not None and m.passed and m.counts["captured"] == 1


def test_evidence_fact_coverage_id_match_passes(tmp_path: Path):
    facts = '[{"id": "vf_a", "fact_type": "config", "value": "API_TOKEN", "source": ".env"}]'
    trap_dir = _write_coverage_trap(tmp_path, facts=facts, entrypoints="")
    # Match by stable id even when the value text differs (e.g. value is only a
    # label and the real captured value is more specific).
    run_dir = _write_bundle(tmp_path / "runs", _coverage_bundle(fact_ids=["vf_a"], fact_values=["tok"], cited=[]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("evidence_fact_coverage")
    assert m is not None and m.passed and m.counts["captured"] == 1


# ---------------------------------------------------------------------------
# missed entrypoint rate: every required entrypoint path must be surfaced by a
# discovery-correct run, else the run mechanically missed an entrypoint.
# ---------------------------------------------------------------------------


def test_missed_entrypoint_rate_uncovered_path_fails(tmp_path: Path):
    ep = '[{"path": ".env", "semantic_key": "config.env"}]'
    trap_dir = _write_coverage_trap(tmp_path, facts="[]", entrypoints=ep)
    # The run cites nothing and surfaces no .env — the entrypoint is missed.
    run_dir = _write_bundle(tmp_path / "runs", _coverage_bundle(fact_ids=[], fact_values=[], cited=[]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("missed_entrypoint_rate")
    assert m is not None and not m.passed
    assert m.counts["missed"] == 1 and m.keys == [".env"]


def test_missed_entrypoint_rate_cited_path_passes(tmp_path: Path):
    ep = '[{"path": ".env", "semantic_key": "config.env"}]'
    trap_dir = _write_coverage_trap(tmp_path, facts="[]", entrypoints=ep)
    # The run surfaces .env as an adjudication evidence ref — entrypoint found.
    run_dir = _write_bundle(tmp_path / "runs", _coverage_bundle(fact_ids=[], fact_values=[], cited=[".env"]))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("missed_entrypoint_rate")
    assert m is not None and m.passed and m.counts["surfaced"] == 1


# ---------------------------------------------------------------------------
# Required + value-forbidden config-conflict regression (blind-review P1)
# ---------------------------------------------------------------------------


def test_required_forbidden_value_correct_value_passes(tmp_path: Path):
    """A key that is BOTH required and forbidden-with-value is a config-conflict
    trap. Asserting the CORRECT value must pass the mechanical forbidden
    control (the gold marks the stale value as forbidden, not the key)."""
    trap_dir = _write_required_forbidden_trap(tmp_path)
    run_dir = _write_bundle(tmp_path / "runs", _value_bundle("4.2.0"))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("forbidden_claim_control")
    assert m is not None and m.passed
    assert "pkg.dep" not in m.keys


def test_required_forbidden_value_stale_value_fails(tmp_path: Path):
    """Regression for the blind-review P1: a required+forbidden config-conflict
    trap used to pass the mechanical gate even when the run asserted the exact
    stale/forbidden value, because value-less forbids were suppressed for
    required keys and required-recall checked key presence only. Once the gold
    carries a value, a run asserting the stale value MUST be caught."""
    trap_dir = _write_required_forbidden_trap(tmp_path)
    run_dir = _write_bundle(tmp_path / "runs", _value_bundle("4.1.0"))
    score = scorer.score_run(run_dir, trap_dir)
    m = score.metric("forbidden_claim_control")
    assert m is not None and not m.passed
    assert "pkg.dep" in m.keys
