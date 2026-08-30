"""Legacy deterministic layer: present-but-isolated, marked non-authoritative.

These tests pin the Cognitive Authority Boundary from the *legacy* side: the
deprecated deterministic renderer still exists (kept for regression / mechanical
fallback), but it is explicitly named LEGACY and it does NOT leak into the
authoritative pipeline namespace. The pipeline is a legacy scaffold; the
authoritative writer is the LLM Language Writer subagent that runs in Claude,
never in pytest.
"""

import makewiki_skills.pipeline.pipeline as pipeline_module
from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import (
    LanguageGenerator,
    LegacyDeterministicRenderer,
)
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.model.semantic_model import SemanticModel
from makewiki_skills.pipeline.pipeline import Pipeline


def test_legacy_renderer_is_named_legacy():
    """The canonical renderer is called ``LegacyDeterministicRenderer`` and
    ``LanguageGenerator`` is just a backward-compatible alias of it."""
    assert LanguageGenerator is LegacyDeterministicRenderer
    assert LegacyDeterministicRenderer.__name__ == "LegacyDeterministicRenderer"


def test_pipeline_is_legacy_scaffold():
    """The pipeline is explicitly a legacy scaffold, and it does NOT re-export
    the ``LanguageGenerator`` name (the legacy writer lives in generator/, not
    pipeline/)."""
    assert Pipeline._LEGACY_WRITER is True
    assert not hasattr(pipeline_module, "LanguageGenerator")


def test_legacy_renderer_still_renders_mechanical_scaffold():
    """Regression guard: the deprecated deterministic renderer still produces a
    ``DocumentArtifact``-typed document from a minimal SemanticModel, so the
    legacy path stays functional in isolation without leaking into the
    authoritative writer."""
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("en")

    model = SemanticModel()
    renderer = LegacyDeterministicRenderer()
    config = MakeWikiConfig.default()

    docs = renderer.generate(model, profile, config)
    assert len(docs) > 0
    assert isinstance(docs[0], DocumentArtifact)
    assert docs[0].language_code == "en"
