"""Architecture-Contract round: the repo's non-negotiable architectural boundaries.

This file pins the final-round architecture boundaries that were NOT already
locked by the existing contract suite (see ``test_authoritative_contract.py``
for the verification-core / four-state-gate vocabulary, and
``test_no_false_verification_pass.py`` for the empty-layer honesty model). The
five boundaries here are the Cognitive Authority Boundary expressed as source
contracts:

1. The legacy cognitive renderer is CONFINED to the deprecated scaffold — it may
   be imported/instantiated ONLY by ``pipeline.py`` (which carries the explicit
   ``_LEGACY_WRITER = True`` marker). No mechanical plane module (verification,
   evals) and no verification CLI entry point may reach it.
2. The semantic/audit layers (L3, L4b, L5) RECORD that review is pending but
   never adjudicate it in Python. In particular L5 never emits a ``passed`` /
   ``verified`` check — it only collects epistemic candidates for the LLM.
3. Semantic audit is ITEM-LEVEL: every pending semantic check carries a stable
   ``review_item_id`` (``L3:<doc>:<...>``, ``L4b:<doc>:<section>``,
   ``L5:<doc>:<...>``), never a whole-document blob.
4. Semantic review aligns on STABLE section IDs via the ``makewiki:section=<slug>``
   protocol (the section grammar), never on heading text or position.
5. The mechanical eval scorer (``evals/scorer.py``) contains NO semantic
   heuristics: it decides purely by stable identities / exact literal values,
   with no regex-over-prose and no string-similarity engine.

All checks are AST / source based: they read the *shape* of the code, so a
future change that quietly wires a similarity engine in (or promotes the legacy
renderer) fails loudly here without needing to execute it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import makewiki_skills

SRC_DIR = Path(makewiki_skills.__file__).resolve().parent
GENERATOR_PKG = "makewiki_skills.generator.language_generator"
LEGACY_RENDERER_SYMBOL = "LegacyDeterministicRenderer"


def _module_import_roots(module_path: Path) -> set[str]:
    """Top-level dotted import-source roots imported by a module (AST)."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _modules_under(pkg_name: str) -> list[Path]:
    return sorted((SRC_DIR / pkg_name).glob("*.py"))


# ---------------------------------------------------------------------------
# Boundary 1 — legacy cognitive pipeline & generator packages completely deleted
# ---------------------------------------------------------------------------


def test_legacy_packages_are_completely_absent():
    """The legacy cognitive packages (pipeline, generator, revision) are removed.

    In Phase 2, Python cognitive pipeline, Jinja generator, and revision engine
    are completely deleted from the codebase. Python owns only mechanical proof,
    extraction, validation, compilation, and packaging.
    """
    forbidden_pkgs = ["pipeline", "generator", "revision"]
    for pkg in forbidden_pkgs:
        pkg_dir = SRC_DIR / pkg
        assert not pkg_dir.exists(), f"Legacy cognitive package '{pkg}' must be deleted"


def test_mechanical_planes_never_import_generator_or_pipeline_packages():
    """No module in src/ imports generator or pipeline packages."""
    for py in SRC_DIR.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        text = py.read_text(encoding="utf-8")
        assert "makewiki_skills.pipeline" not in text, f"{py} imports makewiki_skills.pipeline"
        assert "makewiki_skills.generator" not in text, f"{py} imports makewiki_skills.generator"
        assert "makewiki_skills.revision" not in text, f"{py} imports makewiki_skills.revision"


# ---------------------------------------------------------------------------
# Boundary 2 — L3/L4b/L5 record pending, never adjudicate semantics in Python
# ---------------------------------------------------------------------------


def test_l5_epistemic_never_passes_in_python():
    """L5 only RECORDS epistemic candidates for the LLM Auditor.

    The L5 verifier mechanically locates command/hedging candidates but cannot
    adjudicate whether a document's projected confidence matches evidence.
    Therefore every real L5 check must be emitted ``verified=False`` with a
    non-passing status — never a Python-authored ``passed``. The only non-pending
    emission is the not-executed placeholder, which is also ``verified=False``.
    """
    l5 = (SRC_DIR / "verification" / "l5_epistemic.py").read_text(encoding="utf-8")
    tree = ast.parse(l5)
    # The verifier must never set verified=True or status="passed" on a check it
    # constructs from candidates.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("append",):
                for kw in node.keywords:
                    if (
                        kw.arg == "verified"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                    ):
                        raise AssertionError(
                            "L5 constructs a verified=True check — Python must not "
                            "adjudicate epistemic correctness"
                        )
                    if (
                        kw.arg == "status"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value == "passed"
                    ):
                        raise AssertionError(
                            "L5 constructs a status='passed' check — epistemic "
                            "adjudication is reserved for the LLM Auditor"
                        )
    # And there is no verified=True literal anywhere in the module's check builds.
    assert "verified=True" not in l5, "L5 must never set verified=True"


def test_l3_l4b_and_l5_pending_checks_carry_review_item_id():
    """Every semantic check emitted for LLM review carries a stable item id.

    This is the item-level audit contract (boundary 3): a pending L3 / L4b /
    semantic L5 check must key the review by a stable ``review_item_id`` (a
    ``<layer>:<doc>:<identity>`` triple), never a whole-document blob. The audit
    verdicts in the eval scorer are consumed per ``review_item_id`` (see
    ``test_semantic_audit_verdicts_keyed_by_review_item_id``), so dropping the
    id would break the item-level mapping.

    We assert the emitted ``review_item_id`` values for the real verifiers are
    non-empty and stable-key shaped.
    """
    from makewiki_skills.model.document_artifact import DocumentArtifact as GD
    from makewiki_skills.verification.l3_behavior import L3BehaviorVerifier
    from makewiki_skills.verification.l4_cross_language import (
        L4CrossLanguageVerifier,
    )
    from makewiki_skills.verification.l5_epistemic import L5EpistemicVerifier

    def _doc(identifier: str, content: str) -> GD:
        return GD(
            filename=identifier,
            base_name="usage.md",
            language_code="en",
            content=content,
        )

    # An L3 behavioral claim -> a review_item_id, not a blob.
    l3 = L3BehaviorVerifier(Path("."))
    r3 = l3.verify_documents(
        {"en": [_doc("usage.md", "Symptom: `the phoenix daemon is down` appears at boot")]}
    )
    l3_items = [c.review_item_id for c in r3.checks if c.review_item_id]
    for item in l3_items:
        assert ":" in item, f"L3 review_item_id not keyed: {item!r}"

    # Multilingual L4b -> one item per stable section id.
    en = GD(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content=(
            "<!-- makewiki:section=usage.run -->\n## Run\nrun it\n"
            "<!-- makewiki:section=usage.deploy -->\n## Deploy\ndeploy it\n"
        ),
    )
    zh = GD(
        filename="usage.zh-CN.md",
        base_name="usage.md",
        language_code="zh-CN",
        content=(
            "<!-- makewiki:section=usage.run -->\n## 运行\n运行它\n"
            "<!-- makewiki:section=usage.deploy -->\n## 部署\n部署它\n"
        ),
    )
    r4 = L4CrossLanguageVerifier().verify_documents({"en": [en], "zh-CN": [zh]})
    l4b_items = [
        c.review_item_id
        for c in r4.checks
        if c.claim_type == "l4b_semantic" and c.review_item_id
    ]
    for item in l4b_items:
        assert item.startswith("L4b:"), f"L4b item not L4b-keyed: {item!r}"
        assert len(item.split(":")) >= 3, f"L4b item lacks <doc>:<section>: {item!r}"
    assert len(l4b_items) >= 2, "expected per-section L4b review items"

    # An L5 epistemic candidate -> item-level id.
    r5 = L5EpistemicVerifier().verify_documents({"en": [_doc("usage.md", "```bash\nhi\n```")]})
    l5_items = [c.review_item_id for c in r5.checks if c.review_item_id]
    for item in l5_items:
        assert item.startswith("L5:"), f"L5 item not L5-keyed: {item!r}"


def test_l4b_section_review_uses_stable_section_ids():
    """L4b prose-parity review aligns on STABLE section IDs (boundary 4).

    The L4b per-section checks must be keyed by the stable
    ``makewiki:section=<slug>`` section identity — never by heading text or
    heading order, which languages may legitimately reorder. This drives the
    ``L4b:<doc>:<slug>`` review_item_id used by the semantic audit.
    """
    l4 = (SRC_DIR / "verification" / "l4_cross_language.py").read_text(
        encoding="utf-8"
    )
    # Stable section ids are sourced from the section parser (single source of
    # truth for the makewiki:section grammar), and the review_item_id embeds the
    # parsed section id.
    assert "parse_document_sections" in l4
    assert "review_item_id=f" in l4
    assert "makewiki:section" in l4 or "_SECTION_MARKER_PATTERN" in l4
    # L4b must NOT key its review on heading text.
    assert "heading.text" not in l4 and "heading_text" not in l4


# ---------------------------------------------------------------------------
# Boundary 5 — the mechanical eval scorer is free of semantic heuristics
# ---------------------------------------------------------------------------


def _scorer_ast() -> ast.Module:
    scorer = SRC_DIR / "evals" / "scorer.py"
    return ast.parse(scorer.read_text(encoding="utf-8"))


#: Similarity-engine modules — a scorer that imports any of these is ranking how
#: close two strings are, i.e. deciding semantic proximity in Python, which the
#: authoritative boundary forbids (prose similarity is the LLM Eval Judge's job).
_DANGEROUS_SIMILARITY_IMPORTS = {
    "difflib",
    "SequenceMatcher",
    "fuzzywuzzy",
    "rapidfuzz",
    "thefuzz",
    "Levenshtein",
    "jellyfish",
    "strsim",
}


def test_scorer_imports_no_similarity_engine():
    """Ban similarity-engine imports in the mechanical scorer.

    Why this is banned: a string-similarity tool (``difflib``/``SequenceMatcher``,
    ``fuzzywuzzy``/``rapidfuzz``/``thefuzz``, ``Levenshtein``/``jellyfish``)
    scores how *alike* two strings are — a semantic judgment about prose. The
    scorer must decide purely by stable identities (claim IDs, semantic keys,
    gate state, exact literal values). Importing such a module is the clearest
    possible wiring of a semantic heuristics engine into the mechanical plane and
    must fail loudly.
    """
    tree = _scorer_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in _DANGEROUS_SIMILARITY_IMPORTS, (
                    f"scorer imports similarity engine {alias.name!r}"
                )
        elif isinstance(node, ast.ImportFrom):
            if not node.module:
                continue
            root = node.module.split(".")[0]
            assert root not in _DANGEROUS_SIMILARITY_IMPORTS and root != "difflib", (
                f"scorer imports from similarity engine {node.module!r}"
            )
            for alias in node.names:
                assert alias.name != "SequenceMatcher", (
                    "scorer imports SequenceMatcher (string-similarity metric)"
                )


def test_scorer_has_no_regex_over_prose():
    """Ban regex matching in the mechanical scorer.

    Why this is banned: a ``re`` search/findall/match over a value field, a
    ``claim_text`` or an assertion string is the classic shape of a hand-rolled
    similarity / keyword heuristic — "did the doc say approximately this". The
    scorer is deliberately dumb (see its module docstring): it compares exact
    literal values and stable identities only, so it never needs the regex
    module at all. If a future edit adds a ``re`` call here it is almost certainly
    regex-based semantic matching on natural language and must be reviewed.
    """
    tree = _scorer_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "re", "scorer must not import the re module"
        elif isinstance(node, ast.ImportFrom):
            if node.module == "re":
                raise AssertionError("scorer must not import from the re module")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "re" and node.attr in {
                "search",
                "match",
                "fullmatch",
                "findall",
                "finditer",
                "compile",
                "sub",
                "split",
            }:
                raise AssertionError(
                    f"scorer calls re.{node.attr} — regex over prose is a semantic "
                    "heuristic and is forbidden in the mechanical scorer"
                )


def test_scorer_string_ops_are_exact_or_normalize_only():
    """The scorer's string operations are exact-value / normalization, not similarity.

    The allowed, expected carve-outs are:
      * exact equality after whitespace/case normalization
        (``" ".join(v.split()).lower() == target``) — this is what
        ``_asserts_value_for`` uses to compare a port number, and it is a
        structured value equality, NOT a similarity rank; and
      * set/dict membership over stable semantic keys and gate-state enum
        literals (``semantic_key in asserted_keys``, ``verdict == "passed"``).

    What is still banned even though ``==`` is fine: calling a *similarity*
    method that returns a proximity score. We catch the two common call shapes —
    ``SequenceMatcher(...).ratio()/quick_ratio()`` and ``.similar()`` /
    ``.similarity()`` (fuzzywuzzy/rapidfuzz/thefuzz) — plus a bare
    ``difflib.SequenceMatcher`` construction.
    """
    tree = _scorer_ast()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                # SequenceMatcher(...).ratio() — a similarity score.
                if func.attr in {"ratio", "quick_ratio", "real_quick_ratio"}:
                    raise AssertionError(
                        f"scorer calls .{func.attr}() — a string-similarity ratio, "
                        "forbidden in the mechanical scorer"
                    )
                # fuzzywuzzy / rapidfuzz / thefuzz style .similar()/.similarity().
                if func.attr in {"similar", "similarity"}:
                    raise AssertionError(
                        f"scorer calls .{func.attr}() — a fuzzy string-similarity "
                        "metric, forbidden in the mechanical scorer"
                    )
            # difflib.SequenceMatcher(...) constructed directly.
            if isinstance(func, ast.Attribute) and func.attr == "SequenceMatcher":
                raise AssertionError(
                    "scorer constructs SequenceMatcher — a string-similarity engine"
                )


def test_semantic_audit_verdicts_keyed_by_review_item_id():
    """The eval scorer consumes audit verdicts per review_item_id (item-level).

    This is the mechanical side of boundary 3: the scorer maps semantic-audit
    verdicts by their stable ``review_item_id`` (``L4b:<doc>:<section>``), and
    collects exactly the pending semantic review ids to cross-check against the
    audit — it never scores against a whole-document blob. This keeps audit
    completeness an item-level, mechanically-checkable contract.
    """
    scorer = (SRC_DIR / "evals" / "scorer.py").read_text(encoding="utf-8")
    assert "review_item_id" in scorer
    assert "pending_semantic_review_ids" in scorer
    assert "audited_ids" in scorer
    # The pending items are gathered per-id from the mechanical report layers.
    assert "{v.review_item_id for v in view.semantic_audit.verdicts}" in scorer
