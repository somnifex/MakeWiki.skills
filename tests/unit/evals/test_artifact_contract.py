"""Run-artifact contract (§3): schema version, save/load round-trip, required files."""

from __future__ import annotations

from pathlib import Path

import pytest

from makewiki_skills.evals import artifact


def _make_meta(tmp_path: Path) -> artifact.RunMeta:
    return artifact.RunMeta(
        schema_version=artifact.SCHEMA_VERSION,
        trap="misleading-readme",
        run_id="run-test",
        seed=0,
        host="fixture",
        executed_by="fixture",
    )


def _make_artifacts() -> dict[str, artifact.BaseModel]:
    """A minimal but schema-valid full artifact set."""
    return {
        "evidence.json": artifact.EvidenceArtifact(
            facts=[{"fact_id": "f1", "fact_type": "config", "value": "8080", "source": "app/server.py"}],
            detected_packages=["server"],
        ),
        "agent_claims.json": artifact.AgentClaimsArtifact(
            sets=[
                {
                    "agent_id": "scout-red",
                    "perspective": "user-experience",
                    "claims": [
                        {
                            "claim_type": "config",
                            "semantic_key": "network.port.default",
                            "assertion": "default port is 8080",
                        }
                    ],
                }
            ]
        ),
        "rebattle.json": artifact.RebattleArtifact(
            discrepancies=[
                {
                    "topic": "network.port.default",
                    "participants": ["scout-red", "scout-blue"],
                    "source_values": {"scout-red": "3000", "scout-blue": "8080"},
                }
            ]
        ),
        "adjudications.json": artifact.AdjudicationsArtifact(
            rulings=[
                {
                    "topic": "network.port.default",
                    "ruling": "accepted",
                    "final_assertion": "8080",
                    "verified_via_codebase": True,
                    "evidence_refs": ["app/server.py"],
                    "adjudicator_reasoning": "source wins over stale README",
                }
            ]
        ),
        "semantic_model.json": artifact.SemanticModelArtifact(
            dotenv=[],
            user_tasks=["run the server"],
            troubleshooting=[],
            provenance={"network.port.default": "app/server.py:12"},
            claims=[{"semantic_key": "network.port.default", "value": "8080"}],
        ),
        "semantic_audit.json": artifact.SemanticAuditArtifact(
            auditor="reviewer",
            documents_digest="abc",
            verdicts=[{"review_item_id": "L4b:README:port", "layer": "L4", "status": "accepted", "auditor": "reviewer", "evidence_refs": []}],
            rejected=False,
            rejection_reason="",
        ),
        "mechanical_report.json": artifact.MechanicalReportArtifact(
            layers=[
                {
                    "layer": "L4",
                    "name": "mechanical",
                    "verdict": "passed",
                    "checks": [
                        {
                            "layer": "L4",
                            "claim_type": "l4a_mechanical",
                            "status": "passed",
                            "target": "README.md",
                            "claim_text": "",
                            "review_item_id": "",
                            "detail": "",
                        }
                    ],
                }
            ],
            total_checks=1,
        ),
        "quality_gate.json": artifact.QualityGateArtifact(
            verdict="passed",
            ci_exit_code=0,
            semantic_complete=True,
            pending_llm_layers=[],
            mechanical_passed=True,
        ),
    }


def test_schema_version_is_stable():
    assert artifact.SCHEMA_VERSION == "1.0.0"


def test_run_artifact_map_names_all_required_files():
    names = set(artifact.run_artifact_map().keys())
    assert {"evidence.json", "agent_claims.json", "rebattle.json", "adjudications.json",
            "semantic_model.json", "semantic_audit.json", "mechanical_report.json",
            "quality_gate.json"} <= names


def test_artifact_files_constant_covers_index_and_every_map_entry():
    files = set(artifact.ARTIFACT_FILES)
    assert artifact.RUN_INDEX_FILE in files
    assert set(artifact.run_artifact_map().keys()) <= files


def test_save_load_round_trip(tmp_path: Path):
    meta = _make_meta(tmp_path)
    artifacts = _make_artifacts()
    run_dir = tmp_path / "run"
    artifact.save_run(run_dir, meta, artifacts)
    # Required files exist on disk.
    assert (run_dir / artifact.RUN_INDEX_FILE).is_file()
    for name in artifact.run_artifact_map():
        assert (run_dir / name).is_file(), f"missing {name}"

    meta2, artifacts2 = artifact.load_run(run_dir)
    assert meta2.trap == "misleading-readme"
    assert meta2.run_id == "run-test"
    assert artifacts2["evidence.json"].facts[0]["value"] == "8080"
    assert artifacts2["quality_gate.json"].verdict == "passed"


def test_docs_dir_is_used_and_separate_from_artifacts(tmp_path: Path):
    meta = _make_meta(tmp_path)
    artifacts = _make_artifacts()
    run_dir = tmp_path / "run"
    artifact.save_run(run_dir, meta, artifacts)
    # A writer drop a docs/ md; docs_dir_for points at it and it is disjoint
    # from the artifact files under the run root.
    docs_dir = artifact.docs_dir_for(run_dir)
    assert docs_dir == run_dir / artifact.DOCS_DIR
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "README.md").write_text("# readme", encoding="utf-8")
    assert (docs_dir / "README.md").is_file()
    artifact_files = set(artifact.ARTIFACT_FILES)
    assert artifact.DOCS_DIR not in artifact_files


def test_load_run_rejects_wrong_schema_version(tmp_path: Path):
    meta = _make_meta(tmp_path)
    artifacts = _make_artifacts()
    run_dir = tmp_path / "run"
    artifact.save_run(run_dir, meta, artifacts)
    # Corrupt the schema version and confirm load raises.
    run_json = run_dir / artifact.RUN_INDEX_FILE
    data = run_json.read_text(encoding="utf-8")
    data = data.replace('"1.0.0"', '"9.9.9"', 1)
    run_json.write_text(data, encoding="utf-8")

    with pytest.raises(ValueError):
        artifact.load_run(run_dir)


def test_load_run_raises_on_missing_artifact(tmp_path: Path):
    meta = _make_meta(tmp_path)
    artifacts = _make_artifacts()
    run_dir = tmp_path / "run"
    artifact.save_run(run_dir, meta, artifacts)
    (run_dir / "rebattle.json").unlink()
    with pytest.raises(FileNotFoundError):
        artifact.load_run(run_dir)
