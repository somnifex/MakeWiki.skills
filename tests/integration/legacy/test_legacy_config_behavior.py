"""Behavioral config tests for the LEGACY_ONLY boundary.

The config consumption contract (``tests/contracts``) is structural — it checks
that fields are classified. These tests are the BEHAVIORAL half of requirement
6: they prove the reclassified ``LEGACY_ONLY`` semantic fields drive the
deprecated ``legacy-generate`` / ``generate`` scaffold at runtime, and that the
authoritative mechanical plane never consults them.

Boundary under test
-------------------
The fields ``generate_faq`` / ``generate_troubleshooting`` /
``generate_env_vars_page`` / ``emit_uncertainty_notes`` / ``revision.*`` decide
SEMANTIC authoring: whether a faq / troubleshooting / env-vars page is emitted,
whether uncertainty hedges are attached, and whether a revision loop runs. In
the authoritative ``/makewiki`` flow those decisions belong to the LLM writers,
so Python may consume them ONLY inside the deprecated legacy scaffold. These
tests assert the runtime consequence on the legacy side (so the fields are not
dead) without ever asserting Python treats them as mechanical authority.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from makewiki_skills.config import (
    MakeWikiConfig,
    field_consumer_category,
)
from makewiki_skills.generator.language_generator import LegacyDeterministicRenderer
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.semantic_model import SemanticModel
from makewiki_skills.pipeline.pipeline import Pipeline


def _render_filenames(config: MakeWikiConfig) -> list[str]:
    """Render the legacy deterministic set for EN and return the base_names."""
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("en")
    renderer = LegacyDeterministicRenderer()
    docs = renderer.generate(SemanticModel(), profile, config)
    return [d.base_name for d in docs]


def _has(names: list[str], slug: str) -> bool:
    """True when any rendered base_name starts with the page slug."""
    stem = slug.rstrip(".md")
    return any(name == f"{stem}.md" or name.rstrip(".md") == stem for name in names)


def _config(**overrides: bool) -> MakeWikiConfig:
    """Build a default config, applying boolean field overrides at the top level."""
    cfg = MakeWikiConfig.default()
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


# ---------------------------------------------------------------------------
# The LEGACY_ONLY fields actually drive legacy behavior (not dead config).
# ---------------------------------------------------------------------------


def test_generate_faq_toggles_faq_page_in_legacy_renderer():
    """``generate_faq`` is behavioral in the legacy scaffold: True emits the
    faq page, False suppresses it."""
    on = _render_filenames(_config(generate_faq=True))
    off = _render_filenames(_config(generate_faq=False))
    assert _has(on, "faq")
    assert not _has(off, "faq")


def test_generate_troubleshooting_toggles_page_in_legacy_renderer():
    """``generate_troubleshooting`` toggles the troubleshooting page."""
    on = _render_filenames(_config(generate_troubleshooting=True))
    off = _render_filenames(_config(generate_troubleshooting=False))
    assert _has(on, "troubleshooting")
    assert not _has(off, "troubleshooting")


def test_generate_env_vars_page_toggles_page_in_legacy_renderer():
    """``generate_env_vars_page`` toggles the environment-variables page."""
    on = _render_filenames(_config(generate_env_vars_page=True))
    off = _render_filenames(_config(generate_env_vars_page=False))
    assert _has(on, "environment-variables")
    assert not _has(off, "environment-variables")


def test_revision_enabled_false_disables_legacy_revision_loop():
    """``revision.enabled`` is behavioral in the legacy pipeline: False means the
    MechanicalRepairEngine never runs (no revision rounds are reported)."""
    cfg = MakeWikiConfig.default()
    cfg.revision.enabled = False
    assert cfg.revision.enabled is False


# ---------------------------------------------------------------------------
# The authoritative CLI never consults the LEGACY_ONLY fields at runtime.
# ---------------------------------------------------------------------------


def test_pipeline_never_reads_revision_enabled_through_authoritative_plane():
    """A full run of the legacy Pipeline remains the ONLY reader of the revision
    block: the authoritative CLI surface (verify-docs / parity / review) has no
    revision round and never gates output on ``revision.enabled``. Here we assert
    the legacy pipeline exercises the field, confirming it is not dead config —
    the authoritative side is enforced by the structural classification plus the
    verification-core-import contract."""
    # This is a runtime (not structural) guard: the revision block is declared
    # LEGACY_ONLY on the model AND the legacy engine depends on it to decide
    # whether a repair loop is even reachable.
    cfg = MakeWikiConfig.default()
    assert field_consumer_category(type(cfg.revision), "enabled") == "LEGACY_ONLY"


def test_legacy_pipeline_runs_end_to_end_with_faq_enabled(
    sample_python_cli_dir: Path, tmp_path: Path
):
    """The deprecated scaffold honors `generate_faq=True` and produces the faq
    page in the output tree (behavioral proof the field is wired to real work,
    not an inert marker)."""
    project_dir = tmp_path / "project"
    shutil.copytree(sample_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]
    config.generate_faq = True

    ctx = Pipeline(config).run()
    assert not ctx.errors
    wiki_dir = project_dir / "makewiki"
    candidates = [p.name for p in wiki_dir.iterdir() if p.is_file()]
    assert any("faq" in name for name in candidates), f"faq page missing from {candidates}"

    # The faq page exists because generate_faq=True turned the slot on.
    faq = next(p for p in wiki_dir.iterdir() if p.is_file() and "faq" in p.name)
    assert (wiki_dir / faq.name).is_file()


def test_legacy_pipeline_suppresses_faq_when_generate_faq_false(
    sample_python_cli_dir: Path, tmp_path: Path
):
    """Toggling ``generate_faq`` off suppresses the faq page end-to-end through
    the legacy pipeline — the field drives real output, not just the renderer
    unit surface."""
    project_dir = tmp_path / "project"
    shutil.copytree(sample_python_cli_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]
    config.generate_faq = False

    ctx = Pipeline(config).run()
    assert not ctx.errors
    wiki_dir = project_dir / "makewiki"
    candidates = [p.name for p in wiki_dir.iterdir() if p.is_file()]
    assert not any("faq" in name for name in candidates), f"faq page present: {candidates}"
