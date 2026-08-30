"""Contract: the Cognitive Authority Boundary keeps the mechanical and cognitive
planes strictly separated.

- Every verifier that imports a document type MUST import it from the neutral
  model (``makewiki_skills.model.document_artifact``), never from the legacy
  generator.
- The revision engine and the legacy renderer must NOT author narrative prose in
  Python (no per-language caveat/translation tables).
"""

import ast
from pathlib import Path

import makewiki_skills

SRC_DIR = Path(makewiki_skills.__file__).resolve().parent

NEUTRAL_MODULE = "model.document_artifact"
BANNED_GENERATOR = "language_generator"

# Document-type symbols that must resolve to the neutral model, not the generator.
DOCUMENT_SYMBOLS = {"DocumentArtifact", "GeneratedDocument", "RenderedDocument"}


def _module_imports(module_path: Path):
    """Return from-target -> imported-symbols dict via AST for one module."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    from_targets: dict[str, set[str]] = {}  # full dotted module -> symbols
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                syms = {a.name for a in node.names}
                from_targets.setdefault(node.module, set()).update(syms)
    return from_targets


def _is_neutral_doc_module(module: str) -> bool:
    """True when the dotted module path is the neutral document-artifact model."""
    return module.endswith(NEUTRAL_MODULE)


def test_every_verifier_imports_neutral_document_artifact():
    """Every module under verification that imports a document type must import
    it from ``model.document_artifact`` — never from the legacy generator."""
    verification_dir = SRC_DIR / "verification"
    for module_path in verification_dir.glob("*.py"):
        from_targets = _module_imports(module_path)
        # Any document-type symbol imported must come from the neutral model
        # only; importing it from the generator is banned.
        for src, syms in from_targets.items():
            assert not src.endswith(BANNED_GENERATOR), (
                f"{module_path.name} imports a symbol from the legacy generator"
            )
            if syms & DOCUMENT_SYMBOLS:
                assert _is_neutral_doc_module(src), (
                    f"{module_path.name} imports {syms & DOCUMENT_SYMBOLS} from "
                    f"{src!r}, expected the neutral model document_artifact"
                )


def test_revision_and_renderer_do_not_author_narrative_python():
    """The revision engine and legacy renderer must not contain per-language
    narrative-prose translation tables or fabricated multi-language caveats."""
    revision_engine = SRC_DIR / "revision" / "revision_engine.py"
    language_generator = SRC_DIR / "generator" / "language_generator.py"

    for path in (revision_engine, language_generator):
        text = path.read_text(encoding="utf-8")
        assert "_SIMPLE_TRANSLATIONS" not in text, f"{path.name} carries a translation table"

    # The legacy renderer deliberately keeps UNKNOWN markers English-only; it
    # must NOT carry per-language narrative dictionaries.
    tree = ast.parse(language_generator.read_text(encoding="utf-8"))
    class_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    # No class- or function-level narrative translation table lives in the renderer.
    assert "_SIMPLE_TRANSLATIONS" not in class_names

    # The renderer must expose no module-level narrative translation dictionary.
    module_assigns = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", "") == "_SIMPLE_TRANSLATIONS" for t in node.targets)
    ]
    assert module_assigns == []


def test_config_consumer_categories_include_shared():
    """The SHARED fields consumed by both planes are classified SHARED, proving
    the mechanical plane does consume config that also guides the LLM writer."""
    from makewiki_skills.config import (
        DocumentationPolicyConfig,
        field_consumer_category,
    )

    assert (
        field_consumer_category(DocumentationPolicyConfig, "forbid_unfounded_praise")
        == "SHARED"
    )
    assert (
        field_consumer_category(DocumentationPolicyConfig, "banned_descriptors")
        == "SHARED"
    )
