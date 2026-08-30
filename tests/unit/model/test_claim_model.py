"""Unit tests for Claim and ClaimSet data models and builders."""

from pathlib import Path

import pytest

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


def test_mechanical_assertion_alias_is_claim():
    """MechanicalAssertion is a type alias over the core Claim class."""
    from makewiki_skills.model.claim import Claim, MechanicalAssertion

    assert MechanicalAssertion is Claim
    assert MechanicalAssertion.__name__ == "Claim"


def test_adjudicated_provenance_value():
    """The provenance literal now supports the 'adjudicated' value."""
    from makewiki_skills.model.claim import Claim

    claim = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
        provenance="adjudicated",
    )
    assert claim.provenance == "adjudicated"


def test_model_package_exports_vocabulary():
    """The model package re-exports the unified four-layer claim vocabulary."""
    from makewiki_skills import model

    assert model.MechanicalAssertion is model.Claim
    assert hasattr(model, "AgentClaim")
    assert hasattr(model, "AgentClaimSet")
    assert hasattr(model, "AdjudicatedClaim")


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


def test_l5_is_always_pending_never_auto_passed():
    """High confidence must never make Python assert epistemic (L5) soundness."""
    from pathlib import Path

    from makewiki_skills.model.claim import (
        Claim,
        ClaimEvidence,
        ClaimSet,
        verify_claims_against_codebase,
    )

    claim = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
        confidence="high",
        evidence=[
            ClaimEvidence(
                source_file="src/cli.py",
                raw_text="def run(): ...",
                confidence="high",
            )
        ],
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[claim]), Path("."))
    assert verified.get_by_id("CMD_RUN").verification.l5_epistemic == "pending"

    # Low/inferred confidence still records the uncertainty reason.
    low = Claim(
        claim_id="CMD_LOW",
        claim_type="command",
        semantic_key="cli.command.low",
        subject="myapp",
        predicate="executes",
        object="myapp run",
        confidence="inferred",
    )
    verified_low = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[low]), Path("."))
    assert verified_low.get_by_id("CMD_LOW").verification.l5_epistemic == "pending"
    assert verified_low.get_by_id("CMD_LOW").uncertainty == "Inferred from configuration or heuristic scan"


def test_l0_syntax_check_is_genuine():
    """L0 must pass only for truly well-formed claims, not mere non-empty fields."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    malformed_cases = [
        # bad claim_id pattern
        Claim(
            claim_id="not_a_valid_id!",
            claim_type="command",
            semantic_key="cli.command.run",
            subject="myapp",
            predicate="executes",
            object="myapp run",
        ),
        # NOTE: an unknown claim_type (e.g. "bogus_type") can no longer be
        # constructed here — claim_type is a strict ClaimType Literal that
        # rejects it at model_validate ingress (see
        # test_claim_type_literal_rejects_invalid). L0's claim_type membership
        # check is thus guaranteed at the model boundary.
        # semantic_key not slash/dot-path shaped
        Claim(
            claim_id="CFG_PORT",
            claim_type="config",
            semantic_key="justonepart",
            subject="PORT",
            predicate="configures",
            object="8080",
        ),
        # empty subject
        Claim(
            claim_id="CMD_RUN",
            claim_type="command",
            semantic_key="cli.command.run",
            subject="   ",
            predicate="executes",
            object="myapp run",
        ),
    ]
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=malformed_cases), Path("."))
    for c in verified.claims:
        assert c.verification.l0_syntax != "passed"

    # A genuinely well-formed claim passes L0.
    good = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
    )
    verified_good = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[good]), Path("."))
    assert verified_good.get_by_id("CMD_RUN").verification.l0_syntax == "passed"


def test_l1_command_without_evidence_is_pending_not_passed():
    """A command claim with no high/medium evidence must never be bare-passed."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    claim = Claim(
        claim_id="CMD_RUN",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run",
        confidence="high",  # high confidence alone is not proof of existence
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[claim]), Path("."))
    assert verified.get_by_id("CMD_RUN").verification.l1_existence == "pending"


def test_l1_unhandled_claim_type_is_pending_not_passed():
    """An unhandled claim type means no L1 check ran, so it must be pending."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    claim = Claim(
        claim_id="CMD_RUN",
        claim_type="workflow",
        semantic_key="workflow.auth",
        subject="myapp",
        predicate="authenticates",
        object="auth flow",
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[claim]), Path("."))
    assert verified.get_by_id("CMD_RUN").verification.l1_existence == "pending"


def test_l1_path_with_non_string_object_is_pending():
    """A path claim whose object is not a string gets no existence check -> pending."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    claim = Claim(
        claim_id="PATH_OBJ",
        claim_type="path",
        semantic_key="filesystem.path.obj",
        subject="cfg",
        predicate="exists_in_repository",
        object={"not": "a string"},
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[claim]), Path("."))
    assert verified.get_by_id("PATH_OBJ").verification.l1_existence == "pending"


def test_claim_type_vocabulary_complete():
    """CLAIM_TYPES covers the full cognitive + mechanical vocabulary, no 'ngx'."""
    from makewiki_skills.model.claim import CLAIM_TYPES, ClaimType

    expected = {
        "command",
        "config",
        "path",
        "version",
        "workflow",
        "persona",
        "prerequisite",
        "behavior",
        "error_case",
        "faq_topic",
        "troubleshooting",
        "constraint",
        "capability",
        "architecture",
    }
    assert set(CLAIM_TYPES) == expected
    assert "ngx" not in CLAIM_TYPES
    assert set(ClaimType.__args__) == expected


def test_cognitive_claim_with_non_mechanical_id_passes_l0():
    """A workflow/persona/faq_topic claim with a free-form id (no CMD_/CFG_/
    PATH_/VER_ prefix) PASSES L0 — ids are validated as slugs, not forced to a
    mechanical prefix."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    claims = [
        Claim(
            claim_id="FW_AUTH_FLOW",
            claim_type="workflow",
            semantic_key="workflow.auth",
            subject="myapp",
            predicate="authenticates_users",
            object="login -> token -> refresh",
        ),
        Claim(
            claim_id="PERSONA_CLI_USER",
            claim_type="persona",
            semantic_key="persona.cli_user",
            subject="myapp",
            predicate="assumes_role",
            object="interactive shell user",
        ),
        Claim(
            claim_id="FAQ_INSTALL",
            claim_type="faq_topic",
            semantic_key="faq.install",
            subject="myapp",
            predicate="answers_question",
            object="how do I install?",
        ),
    ]
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=claims), Path("."))
    for c in verified.claims:
        assert c.verification.l0_syntax == "passed", c.claim_id


def test_claim_id_is_slug_not_mechanical_prefix():
    """A mechanical-prefix-free but genuinely well-formed id is accepted; an id
    carrying characters outside a stable slug (e.g. '!') is not."""
    from pathlib import Path

    from makewiki_skills.model.claim import Claim, ClaimSet, verify_claims_against_codebase

    good = Claim(
        claim_id="run.fast",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run --fast",
    )
    verified = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[good]), Path("."))
    assert verified.get_by_id("run.fast").verification.l0_syntax == "passed"

    bad = Claim(
        claim_id="run!fast",
        claim_type="command",
        semantic_key="cli.command.run",
        subject="myapp",
        predicate="executes",
        object="myapp run --fast",
    )
    verified_bad = verify_claims_against_codebase(ClaimSet(project_name="myapp", claims=[bad]), Path("."))
    assert verified_bad.get_by_id("run!fast").verification.l0_syntax != "passed"


def test_claim_type_literal_rejects_invalid():
    """claim_type is a strict ClaimType Literal: an invalid value (historical
    'ngx') raises at ClaimSet.from_llm_json / model_validate ingress, while all
    14 vocabulary types pass."""
    from makewiki_skills.model.claim import ClaimType

    valid_types = list(ClaimType.__args__)
    assert len(valid_types) == 14

    # All 14 valid types ingest cleanly as llm_claim claims.
    for i, ct in enumerate(valid_types):
        data = [
            {
                "claim_id": f"C{i}",
                "claim_type": ct,
                "semantic_key": f"vocab.t{i}",
                "subject": "myapp",
                "predicate": "asserts",
                "object": "x",
            }
        ]
        cs = ClaimSet.from_llm_json("myapp", data)
        assert cs.get_by_id(f"C{i}").claim_type == ct

    # The historical typo is rejected at ingress.
    bogus = [
        {
            "claim_id": "C_NGX",
            "claim_type": "ngx",
            "semantic_key": "vocab.ngx",
            "subject": "myapp",
            "predicate": "asserts",
            "object": "x",
        }
    ]
    with pytest.raises(ValueError):
        ClaimSet.from_llm_json("myapp", bogus)

    # Direct construction is equally rejected.
    with pytest.raises(ValueError):
        Claim(
            claim_id="C_NGX",
            claim_type="ngx",
            semantic_key="vocab.ngx",
            subject="myapp",
            predicate="asserts",
            object="x",
        )
