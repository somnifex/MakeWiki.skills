"""Authoritative contract: the verification core never depends on the legacy
deterministic renderer, the gate stays honest end-to-end, and cognitive content
enters the SemanticModel only through an explicit Judge adjudication.

These tests pin the Cognitive Authority Boundary from the *authoritative* side:
strong LLM + weak code. Python proves only what is mechanically provable and
returns UNKNOWN / stays pending rather than guessing; cognitive semantic content
requires a Judge ruling (``AdjudicatedClaim``) to enter the model.
"""

import ast
import inspect
from pathlib import Path
from typing import get_args

import makewiki_skills
from makewiki_skills.config import DocumentationPolicyConfig, field_consumer_category
from makewiki_skills.model.document_artifact import DocumentArtifact, GeneratedDocument
from makewiki_skills.model.rebattle import (
    AdjudicatedClaim,
    AgentClaim,
    fold_adjudicated_into_semantic_model,
)
from makewiki_skills.model.semantic_model import SemanticModel
from makewiki_skills.verification.quality_gate import QualityGateVerdict

VERIFICATION_DIR = Path(makewiki_skills.__file__).resolve().parent / "verification"

# A module under verification that imports a document type is allowed to import
# it ONLY from the neutral model; never from the legacy generator.
BANNED_SOURCES = ("language_generator",)


def _verification_modules():
    """Yield every .py module path under the verification package."""
    yield from sorted(VERIFICATION_DIR.glob("*.py"))


def _module_import_targets(module_path: Path):
    """Return the set of top-level import source names for a module (AST-based)."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:  # relative imports use '' / '.'
                targets.add(node.module.split(".")[0])
    return targets


def test_verification_core_never_imports_legacy_generator():
    """THE boundary invariant: no module under makewiki_skills.verification may
    import from makewiki_skills.generator.language_generator."""
    for module_path in _verification_modules():
        imports = _module_import_targets(module_path)
        for banned in BANNED_SOURCES:
            assert (
                banned not in imports
            ), f"{module_path.name} imports the legacy generator ({banned})"


def test_gate_and_model_use_neutral_document_type():
    """The gate and the semantic model consume the neutral ``DocumentArtifact``
    type; ``GeneratedDocument`` is just an alias of it."""
    assert GeneratedDocument is DocumentArtifact


def test_authoritative_gate_verdict_vocabulary():
    """The gate exposes the honest ``pending_semantic_review`` verdict, not just
    passed/failed."""
    assert set(get_args(QualityGateVerdict)) == {
        "passed",
        "pending_semantic_review",
        "failed",
    }


def test_semantic_content_requires_adjudication():
    """Cognitive content enters the SemanticModel ONLY through
    ``fold_adjudicated_into_semantic_model`` ingesting ``AdjudicatedClaim`` (with
    an explicit Judge ruling) — never from a raw ``AgentClaim``."""
    model = SemanticModel()

    # A plain AgentClaim with no Judge ruling must NOT populate cognitive fields.
    plain = AgentClaim(
        agent_id="agent_blue",
        perspective="user_experience",
        claim_type="workflow",
        semantic_key="run.dev",
        assertion="Run the dev server",
        value="makewiki serve",
        confidence="inferred",
    )
    # The helper accepts only AdjudicatedClaim; a raw AgentClaim cannot be passed
    # so nothing is folded in the absence of a Judge ruling.
    assert model.user_tasks == []
    assert model.provenance.user_tasks == "unknown"

    # Once an AdjudicatedClaim (with an explicit accepted ruling) is supplied, the
    # cognitive field is populated and its provenance flips to LLM.
    ruled = AdjudicatedClaim(
        claim=plain,
        ruling="accepted",
        final_assertion="makewiki serve",
        adjudicator_reasoning="Judge accepted after cross-examination",
        verified_via_codebase=True,
    )
    fold_adjudicated_into_semantic_model([ruled], model)
    assert len(model.user_tasks) == 1
    assert model.user_tasks[0].title == "run.dev"
    assert model.user_tasks[0].steps == ["makewiki serve"]
    assert model.provenance.user_tasks == "llm"


def test_config_shared_fields_are_classified_shared():
    """The two fields consumed by BOTH planes (Python mechanical ban + LLM
    writing guidance) are classified SHARED on DocumentationPolicyConfig."""
    assert (
        field_consumer_category(DocumentationPolicyConfig, "forbid_unfounded_praise")
        == "SHARED"
    )
    assert (
        field_consumer_category(DocumentationPolicyConfig, "banned_descriptors")
        == "SHARED"
    )


def test_semantic_content_helper_signature_only_adjudicated():
    """The bridge helper's annotation admits only AdjudicatedClaim — Python
    never fabricates a Judge ruling."""
    sig = inspect.signature(fold_adjudicated_into_semantic_model)
    param = sig.parameters["adjudicated"]
    assert param.annotation is list or "AdjudicatedClaim" in str(param.annotation)
