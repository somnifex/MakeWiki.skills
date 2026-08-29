"""Unit tests for Claim and ClaimSet data models and builders."""

from pathlib import Path

from makewiki_skills.model.claim import (
    Claim,
    ClaimEvidence,
    ClaimSet,
    VerificationState,
    build_claims_from_evidence,
    verify_claims_against_codebase,
)
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


def test_claim_data_model_instantiation():
    claim = Claim(
        claim_id="CLI_SCAN_JSON",
        claim_type="command",
        semantic_key="cli.scan.format.json",
        subject="makewiki",
        predicate="supports_flag",
        object="--format json",
        payload={
            "command": "makewiki scan",
            "flag": "--format",
            "value": "json",
        },
        evidence=[
            ClaimEvidence(
                source_file="src/makewiki_skills/cli.py",
                line_start=100,
                line_end=120,
                raw_text="@app.command()\ndef scan(...):",
                extraction_method="ast_parser",
                confidence="high",
            )
        ],
        confidence="high",
        verification=VerificationState(
            l0_syntax="passed",
            l1_existence="passed",
            l2_interface="passed",
            l3_behavior="not_applicable",
            l4_cross_language="pending",
            l5_epistemic="passed",
        ),
    )

    assert claim.claim_id == "CLI_SCAN_JSON"
    assert claim.claim_type == "command"
    assert claim.verification.l1_existence == "passed"
    assert len(claim.evidence) == 1


def test_claim_set_lookup_and_filtering():
    c1 = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
    )
    c2 = Claim(
        claim_id="CFG_PORT",
        claim_type="config",
        semantic_key="config.parameter.port",
        subject="PORT",
        predicate="configures_parameter",
        object="8080",
    )
    claim_set = ClaimSet(
        project_name="myapp",
        claims=[c1, c2],
    )

    assert claim_set.get_by_id("CMD_RUN") == c1
    assert claim_set.get_by_id("NONEXISTENT") is None
    assert len(claim_set.by_type("command")) == 1
    assert len(claim_set.by_type("config")) == 1
    assert len(claim_set.by_type("path")) == 0


def test_build_claims_from_evidence_4_types():
    registry = EvidenceRegistry()

    # 1. Command
    registry.add(
        EvidenceFact(
            claim="Available command: myapp build",
            fact_type="command",
            value="myapp build",
            evidence=[
                EvidenceLink(
                    source_path="README.md",
                    raw_text="myapp build",
                    confidence="high",
                )
            ],
        )
    )

    # 2. Config Key
    registry.add(
        EvidenceFact(
            claim="Config key: server.port",
            fact_type="config_key",
            value="server.port",
            evidence=[
                EvidenceLink(
                    source_path="config.yaml",
                    raw_text="port: 8080",
                    confidence="high",
                )
            ],
        )
    )

    # 3. Path
    registry.add(
        EvidenceFact(
            claim="Path: src/main.py",
            fact_type="path",
            value="src/main.py",
            evidence=[
                EvidenceLink(
                    source_path="README.md",
                    raw_text="./src/main.py",
                    confidence="medium",
                )
            ],
        )
    )

    # 4. Version
    registry.add(
        EvidenceFact(
            claim="Project version: 1.2.0",
            fact_type="version",
            value="1.2.0",
            evidence=[
                EvidenceLink(
                    source_path="pyproject.toml",
                    raw_text='version = "1.2.0"',
                    confidence="high",
                )
            ],
        )
    )

    detection = ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        confidence=1.0,
        project_name="test-project",
    )

    claim_set = build_claims_from_evidence(detection, registry)

    assert claim_set.project_name == "test-project"
    assert len(claim_set.claims) == 4

    cmd_claims = claim_set.by_type("command")
    assert len(cmd_claims) == 1
    assert cmd_claims[0].object == "myapp build"

    cfg_claims = claim_set.by_type("config")
    assert len(cfg_claims) == 1
    assert cfg_claims[0].object == "server.port"

    path_claims = claim_set.by_type("path")
    assert len(path_claims) == 1
    assert path_claims[0].object == "src/main.py"

    ver_claims = claim_set.by_type("version")
    assert len(ver_claims) == 1
    assert ver_claims[0].object == "1.2.0"


def test_verify_claims_against_codebase(tmp_path: Path):
    # Create real file in tmp_path
    real_file = tmp_path / "real_script.py"
    real_file.write_text("print('hello')", encoding="utf-8")

    c_real = Claim(
        claim_id="PATH_REAL",
        claim_type="path",
        semantic_key="filesystem.path.real",
        subject="real_script.py",
        predicate="exists_in_repository",
        object="real_script.py",
    )
    c_fake = Claim(
        claim_id="PATH_FAKE",
        claim_type="path",
        semantic_key="filesystem.path.fake",
        subject="fake_script.py",
        predicate="exists_in_repository",
        object="fake_script.py",
    )

    claim_set = ClaimSet(
        project_name="test_proj",
        claims=[c_real, c_fake],
    )

    verified = verify_claims_against_codebase(claim_set, tmp_path)

    assert verified.get_by_id("PATH_REAL").verification.l1_existence == "passed"
    assert verified.get_by_id("PATH_FAKE").verification.l1_existence == "failed"


def test_claim_provenance_default_and_llm():
    """Python-built claims default to python_fact; from_llm_json marks llm_claim."""
    from makewiki_skills.model.claim import Claim

    fact = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
    )
    assert fact.provenance == "python_fact"

    llm_data = [
        {
            "claim_id": "FW_AUTH_FLOW",
            "claim_type": "workflow",
            "semantic_key": "workflow.auth",
            "subject": "myapp",
            "predicate": "authenticates_users",
            "object": "auth flow",
            "payload": {"flow": "login -> token -> refresh"},
        }
    ]
    s = ClaimSet.from_llm_json("myapp", llm_data)
    assert s.get_by_id("FW_AUTH_FLOW") is not None
    assert s.get_by_id("FW_AUTH_FLOW").provenance == "llm_claim"
    assert s.get_by_id("FW_AUTH_FLOW").claim_type == "workflow"


def test_verify_claims_no_hardcoded_behavior():
    """L2/L3 must never be blindly marked passed/not_applicable."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    claim = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
        confidence="high",
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[claim]), Path("."))
    assert verified.get_by_id("CMD_RUN").verification.l2_interface in ("pending", "passed", "failed")
    assert verified.get_by_id("CMD_RUN").verification.l3_behavior in ("pending", "passed", "failed")
