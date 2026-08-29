"""Contract tests for the unified four-layer claim vocabulary.

These guard against the historical ambiguity where two unrelated classes both
named ``Claim``/``ClaimSet`` lived in ``model.claim`` and ``model.rebattle``.
Stream 2 renames the ReBattle family to ``AgentClaim``/``AgentClaimSet`` and
introduces ``MechanicalAssertion`` + ``AdjudicatedClaim`` so each layer has a
canonical, unambiguous name.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import makewiki_skills.model as model
from makewiki_skills.model.claim import Claim as CoreClaim
from makewiki_skills.model.rebattle import AdjudicatedClaim, AgentClaim, AgentClaimSet
from makewiki_skills.model.rebattle import Claim as ReBattleClaimAlias
from makewiki_skills.model.rebattle import ClaimSet as ReBattleClaimSetAlias


def test_quadruple_vocabulary_importable() -> None:
    """All four layer names are importable from the model package."""
    assert model.AgentClaim is AgentClaim
    assert model.AgentClaimSet is AgentClaimSet
    assert model.AdjudicatedClaim is AdjudicatedClaim
    assert model.MechanicalAssertion is CoreClaim

    # Each canonical name imports directly from its owning module.
    from makewiki_skills.model.claim import MechanicalAssertion
    from makewiki_skills.model.rebattle import (
        AdjudicatedClaim as RebAdj,
    )
    from makewiki_skills.model.rebattle import (
        AgentClaim as RebAgent,
    )
    from makewiki_skills.model.rebattle import (
        AgentClaimSet as RebSet,
    )

    assert MechanicalAssertion is CoreClaim
    assert RebAgent is AgentClaim
    assert RebSet is AgentClaimSet
    assert RebAdj is AdjudicatedClaim


def test_no_ambiguous_shared_bare_claim() -> None:
    """The bare name 'Claim' is never ambiguously shared across layers.

    ``model.rebattle.Claim`` is a *deprecated alias* to ``AgentClaim``; it is a
    different class from ``model.claim.Claim`` (the core mechanical claim).
    """
    # rebattle.Claim is an alias to AgentClaim, not a distinct class.
    assert ReBattleClaimAlias is AgentClaim
    assert ReBattleClaimSetAlias is AgentClaimSet

    # cli.py imports ClaimSet from both modules. Only one of those names is the
    # rebattle one; they must NOT be the same class.
    from makewiki_skills.model.claim import ClaimSet as CoreClaimSet

    assert ReBattleClaimSetAlias is not CoreClaimSet

    # The core Claim and the AgentClaim are genuinely distinct classes.
    assert AgentClaim is not CoreClaim

    # model.claim.Claim is NOT the same as model.rebattle.AgentClaim.
    assert model.Claim is CoreClaim
    assert model.Claim is not AgentClaim


def test_no_ambiguous_bare_claim_import_collision_in_src() -> None:
    """No source scope imports bare ``Claim``/``ClaimSet`` from BOTH model modules.

    The historical hazard: one scope does both ``from model.rebattle import
    Claim, ClaimSet`` and ``from model.claim import Claim, ClaimSet``, so the
    last import silently shadows the other. Imports in *separate* functions or
    scopes of the same file are fine (e.g. a CLI command module that pulls the
    rebattle ClaimSet in one command and the core ClaimSet in another) — no
    namespace collides there.
    """
    import re

    src_dir = Path(__file__).resolve().parents[2] / "src"

    # Match lines importing bare names from either model module.
    import_line = re.compile(
        r"^(?P<indent> *)(?:from|import)\s+makewiki_skills\.model\."
        r"(?P<module>claim|rebattle)\s+import\s+(?P<names>[A-Za-z0-9_,\s()]+)"
    )

    collisions: list[str] = []
    for py in src_dir.rglob("*.py"):
        # For each import, record which module supplies a bare name within its
        # enclosing scope (identified by the tuple of enclosing block starts).
        modules_for_name_in_scope: dict[tuple, dict[str, set[str]]] = {}

        # block stack: list of (indent, block_id) for each open def/class/block.
        stack: list[tuple[int, int]] = []
        block_counter = 0

        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.lstrip()

            # Pop blocks whose indent is no longer enclosing this line.
            while stack and indent <= stack[-1][0]:
                stack.pop()

            m = import_line.match(line)
            if m:
                scope_key = tuple(stack)
                module = m.group("module")
                for name in re.split(r"[,\s()]+", m.group("names")):
                    name = name.strip()
                    if not name or name not in {"Claim", "ClaimSet"}:
                        continue
                    slot = modules_for_name_in_scope.setdefault(
                        (scope_key, name), {}
                    )
                    slot.setdefault(module, set())
                continue

            # Open a new block for function/class/control bodies.
            if stripped and stripped.endswith(":") and not stripped.startswith(("#", "//")):
                block_counter += 1
                stack.append((indent, block_counter))

        for (scope_key, name), modules in modules_for_name_in_scope.items():
            if modules.keys() == {"claim", "rebattle"}:
                collisions.append(
                    f"{py}: bare '{name}' imported from both claim and rebattle "
                    f"in the same scope (blocks {scope_key})"
                )

    assert collisions == [], "Ambiguous bare Claim imports:\n" + "\n".join(collisions)


def test_src_uses_deprecated_or_canonical_rebattle_names() -> None:
    """The rebattle family no longer needs a NEW bare-distinct Claim; any
    remaining bare 'ClaimSet' import from rebattle.is the deprecated alias.
    """
    from makewiki_skills.model.claim import ClaimSet as CoreClaimSet

    # The rebattle ClaimSet (deprecated alias) is AgentClaimSet, distinct from
    # the core ClaimSet.
    assert ReBattleClaimSetAlias is AgentClaimSet
    assert ReBattleClaimSetAlias is not CoreClaimSet
    assert AgentClaimSet is not CoreClaimSet


def test_all_three_importable_via_python_subprocess() -> None:
    """A fresh interpreter can import every canonical name (guards stale caches)."""
    code = (
        "from makewiki_skills.model import "
        "AgentClaim, AgentClaimSet, MechanicalAssertion, AdjudicatedClaim; "
        "from makewiki_skills.model.rebattle import AgentClaim as A2; "
        "assert AgentClaim is A2"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parents[2]),
    )
    assert result.returncode == 0, result.stderr
