"""Live verifier contract.

Pins the authoritative L0-L5 classes the :class:`VerificationOrchestrator`
actually runs to the tool names the skill corpus documents
(``references/grounding_policy.md``), and forbids re-wiring any legacy
prose-regex "grounding" heuristic (``CodeGroundingVerifier`` / its
``_is_hedged_*`` upgrade logic) back into ``cli.py`` or the verification
``__init__``. This closes a latent boundary gap that the older
``test_cognitive_authority_boundary`` suite does not cover: that suite only
banned ``MechanicalRepairEngine`` / ``RevisionEngine`` / ``language_generator``,
so a future re-introduction of a keyword-based claim->grounded pass would slip
through.

Rule: Python MAY verify existence mechanically (L0/L1/L2/L4a), but must NEVER
promote a claim to grounded/passed via prose-keyword heuristics — that is
L5-epistemic, LLM-judged.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.verification import (
    L0SyntaxVerifier,
    L1ExistenceVerifier,
    L2InterfaceVerifier,
)
from makewiki_skills.verification.orchestrator import VerificationOrchestrator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GROUNDING_POLICY = PROJECT_ROOT / "references" / "grounding_policy.md"
VERIFICATION_INIT = PROJECT_ROOT / "src" / "makewiki_skills" / "verification" / "__init__.py"
CLI_PY = PROJECT_ROOT / "src" / "makewiki_skills" / "cli.py"

# The authoritative layer -> tool mapping must live here once, mirroring
# grounding_policy.md.
LIVE_L0 = L0SyntaxVerifier
LIVE_L1 = L1ExistenceVerifier
LIVE_L2 = L2InterfaceVerifier


def test_orchestrator_runs_documented_live_verifiers():
    """The orchestrator's L0/L1/L2 are exactly the documented classes."""
    from pathlib import Path as _Path

    orch = VerificationOrchestrator(_Path("."))
    assert isinstance(orch.l0, LIVE_L0)
    assert isinstance(orch.l1, LIVE_L1)
    assert isinstance(orch.l2, LIVE_L2)


def test_grounding_policy_names_the_live_l0_tool():
    """grounding_policy.md must cite the real L0 class, not a stale alias."""
    text = GROUNDING_POLICY.read_text(encoding="utf-8")
    assert "CodeGroundingVerifier" not in text
    assert "L0SyntaxVerifier" in text
    assert "L2InterfaceVerifier" in text


def test_legacy_regex_grounder_not_importable_from_live_layer():
    """CodeGroundingVerifier / _is_hedged_* must not be reachable from cli."""
    cli_text = CLI_PY.read_text(encoding="utf-8")
    init_text = VERIFICATION_INIT.read_text(encoding="utf-8")
    assert "CodeGroundingVerifier" not in cli_text
    assert "CodeGroundingVerifier" not in init_text
    assert "_is_hedged" not in cli_text
    assert "_is_hedged" not in init_text


def test_verification_exports_no_legacy_grounding_symbols():
    """__all__ must not re-export the deleted grounding/codebase surface."""
    import makewiki_skills.verification as verification

    for symbol in (
        "CodeGroundingVerifier",
        "CodebaseVerifier",
        "GroundingReport",
        "GroundingViolation",
        "GroundingClaim",
        "CodebaseCheck",
        "CodebaseVerificationReport",
    ):
        assert not hasattr(verification, symbol), (
            f"verification re-exports removed legacy symbol {symbol}"
        )
