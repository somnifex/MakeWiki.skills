"""Tests for CodeGroundingVerifier."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink
from makewiki_skills.verification.code_grounding_verifier import CodeGroundingVerifier


def _registry_with_facts() -> EvidenceRegistry:
    reg = EvidenceRegistry()
    reg.add(EvidenceFact(
        claim="Command: make test",
        fact_type="command",
        value="make test",
        evidence=[EvidenceLink(source_path="Makefile", raw_text="test:", confidence="high")],
    ))
    reg.add(EvidenceFact(
        claim="Command: make serve",
        fact_type="command",
        value="make serve",
        evidence=[EvidenceLink(source_path="Makefile", raw_text="serve:", confidence="high")],
    ))
    reg.add(EvidenceFact(
        claim="Config: server.port",
        fact_type="config_key",
        value="server.port",
        evidence=[EvidenceLink(source_path="config.yaml", raw_text="port: 8080", confidence="high")],
    ))
    reg.add(EvidenceFact(
        claim="Path: src/main.py",
        fact_type="path",
        value="src/main.py",
        evidence=[EvidenceLink(source_path="src/main.py", raw_text="src/main.py", confidence="high")],
    ))
    return reg


def test_grounded_commands_pass():
    """Document with commands that exist in evidence -> no violations."""
    registry = _registry_with_facts()
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# App\n\n```bash\nmake test\nmake serve\n```\n",
    )
    verifier = CodeGroundingVerifier(registry)
    report = verifier.verify({"en": [doc]})

    assert report.passed
    assert report.grounding_score > 0.5


def test_hallucinated_command_detected():
    """Document with a command not in evidence -> violation."""
    registry = _registry_with_facts()
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# App\n\n```bash\nmake deploy-prod\n```\n",
    )
    verifier = CodeGroundingVerifier(registry)
    report = verifier.verify({"en": [doc]})

    assert len(report.violations) > 0
    assert any(v.claim.claim_text == "make deploy-prod" for v in report.violations)


def test_generic_commands_not_flagged():
    """Generic commands like 'pip install' should not be flagged."""
    registry = _registry_with_facts()
    doc = GeneratedDocument(
        filename="install.md",
        base_name="install.md",
        language_code="en",
        content="# Install\n\n```bash\npip install -e .\ngit clone repo\n```\n",
    )
    verifier = CodeGroundingVerifier(registry)
    report = verifier.verify({"en": [doc]})

    cmd_violations = [v for v in report.violations if v.claim.claim_type == "command"]
    cmd_texts = [v.claim.claim_text for v in cmd_violations]
    assert "pip install -e ." not in cmd_texts
    assert "git clone repo" not in cmd_texts


def test_config_key_grounded():
    """Config key from evidence -> not flagged."""
    registry = _registry_with_facts()
    doc = GeneratedDocument(
        filename="config.md",
        base_name="config.md",
        language_code="en",
        content="# Config\n\nSet `server.port` to your preferred port.\n",
    )
    verifier = CodeGroundingVerifier(registry)
    report = verifier.verify({"en": [doc]})
    key_violations = [v for v in report.violations if v.claim.claim_type == "config_key"]
    key_texts = [v.claim.claim_text for v in key_violations]
    assert "server.port" not in key_texts


def test_low_confidence_warning():
    """Command with low-confidence evidence -> low_confidence violation."""
    registry = EvidenceRegistry()
    registry.add(EvidenceFact(
        claim="Command: make deploy",
        fact_type="command",
        value="make deploy",
        evidence=[EvidenceLink(source_path="README.md", raw_text="deploy", confidence="low")],
    ))
    doc = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content="# App\n\n```bash\nmake deploy\n```\n",
    )
    verifier = CodeGroundingVerifier(registry)
    report = verifier.verify({"en": [doc]})

    assert any(v.violation_type == "low_confidence" for v in report.violations)
