"""Cognitive Authority Boundary contract.

This contract enforces the Stream-3 invariant on the Cognitive Authority
Boundary (CLAUDE.md): Python performs MECHANICAL proof only and never exercises
semantic judgment. Specifically it regresses the four degradation points:

1. ``MechanicalRepairEngine`` (formerly ``RevisionEngine``) is mechanical-only:
   it is never wired into the authoritative ``/makewiki`` flow and its repair
   loop never rewrites semantic prose / anti-cliché.
2. The quick-start selection in ``language_generator.py`` no longer guesses by
   the word "start" in a title — it requires an explicit ``is_quick_start`` flag.
3. Config-file classification in ``pipeline.py`` no longer decides narrative
   ("user-facing" vs "manifest"); it records the raw filename as a neutral label.
4. Cross-language code-block parity is keyed by stable ``[[id:...]]`` block IDs,
   never by position.

Plus a regression guard: the deterministic install/prerequisite builders never
fabricate ``pip install -e .`` / ``npm install`` / ``cargo`` / ``go get`` defaults.
"""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import LanguageGenerator
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.semantic_model import (
    InstallationGuide,
    InstallStep,
    ProjectIdentity,
    SemanticModel,
    UsageExample,
)
from makewiki_skills.revision.revision_engine import MechanicalRepairEngine
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD = PROJECT_ROOT / "SKILL.md"
REVISION_ENGINE = PROJECT_ROOT / "src/makewiki_skills/revision/revision_engine.py"
GENERATOR = PROJECT_ROOT / "src/makewiki_skills/generator/language_generator.py"
PIPELINE = PROJECT_ROOT / "src/makewiki_skills/pipeline/pipeline.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_repair_engine_not_in_authoritative_flow():
    """The authoritative ``/makewiki`` revision loop is the LLM Auditor's.

    The mechanical ``MechanicalRepairEngine`` is a deterministic-pipeline
    construct; SKILL.md's Phase 4 revision loop is "Auditor edits Markdown in
    place until Quality Gate passes". The engine must not be part of that
    authoritative narrative revision.
    """
    skill = _read(SKILL_MD)
    # The authoritative flow does not name the Python repair engine.
    assert "MechanicalRepairEngine" not in skill
    assert "RevisionEngine" not in skill
    # And the authoritative revision loop is explicitly the LLM Auditor's.
    assert "Auditor edits Markdown in place" in skill


def test_repair_loop_has_no_anti_cliche_semantic_rewrite():
    """``revise()`` must not rewrite prose/anti-cliché in the normal repair loop."""
    src = _read(REVISION_ENGINE)
    # The old semantic method name is gone.
    assert "_sanitize_ai_cliches" not in src
    # The legacy helper exists but is gated behind the explicit scaffold flag.
    assert "_legacy_anti_cliche_cleanup" in src
    assert "legacy_anti_cliche" in src
    # It is only invoked when that flag is True.
    assert "if self.legacy_anti_cliche:" in src


def test_quick_start_no_substring_heuristic():
    """Quick-start selection requires an explicit flag, not a 'start' substring."""
    src = _read(GENERATOR)
    assert '"start" in example.title.lower()' not in src
    assert '"start" in task.title.lower()' not in src
    # The explicit LLM-authored flag is used instead.
    assert "is_quick_start" in src
    # And an honest UNKNOWN marker exists when nothing is flagged.
    assert "No explicit quick-start example was identified" in src


def test_config_classification_is_mechanical():
    """pipeline.py no longer decides narrative config labels."""
    src = _read(PIPELINE)
    # The fuzzy narrative classifier is removed.
    assert "_is_user_facing_config" not in src
    assert "_MANIFEST_CONFIG_FILES" not in src
    # The neutral label path records the raw filename, not narrative prose.
    assert "_configuration_section_name" in src
    # No narrative "Environment variables" / "Configuration file" decision here.
    assert 'return "Environment variables"' not in src
    assert 'return "Configuration file"' not in src
    # Only an EXACT, mechanical build-metadata exclusion remains (provable by
    # filename), never a fuzzy "config/settings/appsettings/doc" token guess.
    assert "_BUILD_METADATA_FILES" in src
    assert "Path(source).name in _BUILD_METADATA_FILES" in src
    assert '"config" in name' not in src and '"settings" in name' not in src
    assert '"doc" in name' not in src and '"appsettings" in name' not in src
    # Command descriptions are never fabricated from boilerplate.
    assert "CLI entrypoint exposed by the project." not in src
    assert 'if claim.startswith("CLI entrypoint:"):\n        return None' in src


def test_stable_block_id_convention_exists_and_is_honored():
    """Cross-language parity uses stable ``[[id:...]]`` IDs, not position."""
    src = _read(REVISION_ENGINE)
    assert "[[id:" in src or "[[id:%%s]" in src or "_BLOCK_ID_PATTERN" in src
    assert "_extract_blocks_by_id" in src

    # Behavioral: the harmonizer keys blocks by their stable ID.
    content = (
        "# Doc\n\n"
        "[[id:getting_started.install]]\n```bash\nmake setup\n```\n\n"
        "[[id:usage.deploy]]\n```bash\nmake deploy\n```\n"
    )
    blocks = MechanicalRepairEngine._extract_blocks_by_id(content)
    assert set(blocks.keys()) == {"getting_started.install", "usage.deploy"}
    assert "make setup" in blocks["getting_started.install"][0]
    assert "make deploy" in blocks["usage.deploy"][0]


def test_install_and_prerequisites_never_fabricate_defaults():
    """``_build_installation`` / ``_build_prerequisites`` refuse semantic fallback.

    Python must not inject a guessed default like ``pip install -e .`` or a
    canned ``npm install`` when no install command is proven.
    """
    registry = EvidenceRegistry()
    detection = ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        project_name="bare",
        project_dir=".",
    )

    from makewiki_skills.pipeline import pipeline as _pipeline

    installation = _pipeline._build_installation(registry, detection)
    assert installation.steps == []  # no fabricated install step

    prereqs = _pipeline._build_prerequisites(registry, detection)
    assert prereqs == []  # no assumed runtime when none is declared

    # Static guard: pipeline.py never CONSTRUCTS a step with a canned default
    # install command (docstring mentions are allowed; code literals are not).
    import re

    src = _read(PIPELINE)
    assert not re.search(
        r"commands=\[\s*[\"'](?:pip install -e \.|npm install|cargo build|go get)",
        src,
    )


def test_legacy_anti_cliche_flag_defaults_to_false():
    """The legacy scaffold flag is opt-in, disabled by default."""
    engine = MechanicalRepairEngine()
    assert engine.legacy_anti_cliche is False
    engine_on = MechanicalRepairEngine(legacy_anti_cliche=True)
    assert engine_on.legacy_anti_cliche is True


def test_uncertainty_marker_reachable_from_generator():
    """The UNKNOWN quick-start marker flows through ``LanguageGenerator``."""
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("en")
    config = MakeWikiConfig.default()
    config.emit_uncertainty_notes = True

    model = SemanticModel(
        identity=ProjectIdentity(name="app"),
        installation=InstallationGuide(
            steps=[InstallStep(order=1, title="Install", commands=["npm install"])]
        ),
        usage_examples=[UsageExample(title="Get Started Fast", commands=["app go"])],
        project_type=ProjectType.GENERIC,
    )
    gen = LanguageGenerator()
    docs = gen.generate(model, profile, config)
    readme = next(d for d in docs if d.base_name == "README.md")
    assert "Get Started Fast" not in readme.content
    assert "No explicit quick-start example was identified for this project." in readme.content
