"""Config Consumption Contract: every MakeWikiConfig field is consumed.

This contract enforces the Phase-6 invariant from the encapsulation plan:

> Every field in ``makewiki.config.yaml`` is either Python-consumed
> (mechanical plane) or LLM-consumed (Skill orchestrator / writers).
> No field is dead.

The contract is purely structural — it walks the pydantic models and checks
that the union of ``_PYTHON_CONSUMED_FIELDS`` and ``_LLM_CONSUMED_FIELDS``
covers every attribute on every config model. It also confirms that the
subset of fields declared as Python-consumed is actually referenced somewhere
in the ``src/`` tree (catching the common mistake of marking a field as
Python-consumed but never wiring it up).
"""

from __future__ import annotations

import re
from pathlib import Path

from makewiki_skills.config import (
    DocumentationPolicyConfig,
    all_field_categories,
    field_consumer_category,
    iter_config_models,
    legacy_consumed_field_paths,
    llm_consumed_field_paths,
    python_consumed_field_paths,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"


def _all_config_field_paths() -> dict[str, set[str]]:
    """Map each config class to its declared (non-ClassVar) attribute names."""
    fields: dict[str, set[str]] = {}
    for model in iter_config_models():
        names = set()
        for attr_name in model.model_fields:
            names.add(attr_name)
        fields[model.__name__] = names
    return fields


def test_every_config_field_is_marked_consumed():
    """Union of Python + LLM (+ Legacy) consumed sets == every declared field.

    LEGACY_ONLY fields are consumed by the deprecated ``legacy-generate``
    scaffold; they still count as consumed (never dead) but must NOT be treated
    as authoritative mechanical enforcement, so they live outside the Python
    and LLM sets and are counted separately here.
    """
    declared = _all_config_field_paths()
    python_paths = python_consumed_field_paths()
    llm_paths = llm_consumed_field_paths()
    legacy_paths = legacy_consumed_field_paths()

    failures: list[str] = []
    for model_name, fields in declared.items():
        consumed_here = {
            p for p in python_paths | llm_paths | legacy_paths
            if p.startswith(f"{model_name}.")
        }
        expected = {f"{model_name}.{f}" for f in fields}
        missing = expected - consumed_here
        if missing:
            failures.append(f"{model_name}: not classified consumed: {sorted(missing)}")
    assert not failures, "\n".join(failures)


def test_config_consumer_classification_complete():
    """Every public config field maps to EXACTLY ONE of the four categories.

    This replaces the old two-bucket union with the four-way contract:
    PYTHON_ONLY / LLM_ONLY / SHARED / LEGACY_ONLY. No field may be UNKNOWN
    (unconsumed) and no field may claim more than one category.
    """
    categories = all_field_categories()
    expected = _all_config_field_paths()
    flat_expected = {
        f"{model_name}.{f}"
        for model_name, fields in expected.items()
        for f in fields
    }

    assert set(categories) == flat_expected, (
        "all_field_categories() must cover exactly the declared public fields; "
        f"missing={sorted(flat_expected - set(categories))}, "
        f"extra={sorted(set(categories) - flat_expected)}"
    )

    unknown = {p for p, cat in categories.items() if cat == "UNKNOWN"}
    assert not unknown, "Every public config field must be consumed; UNKNOWN: " + ", ".join(sorted(unknown))

    # Every category is one of the four legal values.
    legal = {"PYTHON_ONLY", "LLM_ONLY", "SHARED", "LEGACY_ONLY"}
    illegal = {p for p, cat in categories.items() if cat not in legal}
    assert not illegal, "Field mapped to an illegal category: " + ", ".join(sorted(illegal))


def test_shared_fields_are_single_categorized():
    """The genuinely-shared documentation_policy fields are SHARED.

    ``forbid_unfounded_praise`` and ``banned_descriptors`` are read by the
    Python validator (renderer/validator.py) for mechanical enforcement AND by
    the LLM writer as writing guidance, so they must be classified SHARED —
    not LLM_ONLY / PYTHON_ONLY.
    """
    assert (
        field_consumer_category(DocumentationPolicyConfig, "forbid_unfounded_praise")
        == "SHARED"
    )
    assert (
        field_consumer_category(DocumentationPolicyConfig, "banned_descriptors")
        == "SHARED"
    )


def test_shared_fields_are_read_by_python():
    """SHARED fields must be referenced somewhere in ``src/``.

    This guards the mechanical half of SHARED: a field read only by the LLM
    writer but marked SHARED would silently reclassify a dead or unused slot.
    """
    referenced: list[str] = [
        f"{DocumentationPolicyConfig.__name__}.{field}"
        for field in ("forbid_unfounded_praise", "banned_descriptors")
    ]
    src_texts: dict[str, str] = {
        str(p): p.read_text(encoding="utf-8")
        for p in SRC_ROOT.rglob("*.py")
    }
    missing: list[str] = []
    for dotted in referenced:
        _, _, attr = dotted.rpartition(".")
        pattern = re.compile(
            r"(?:\." + re.escape(attr) + r"\b|\[\s*['\"]" + re.escape(attr) + r"['\"]\s*\])"
        )
        if not any(pattern.search(text) for text in src_texts.values()):
            missing.append(dotted)
    assert not missing, "SHARED fields missing a Python read: " + ", ".join(missing)


def test_llm_only_fields_are_not_python_read():
    """LLM_ONLY documentation_policy fields are NOT consumed by Python.

    This is the negative half of the contract: fields classified LLM_ONLY must
    stay out of the mechanical plane. ``audience`` and friends are only
    consulted by the Skill orchestrator / writers.
    """
    llm_only = [
        field
        for field in DocumentationPolicyConfig.model_fields
        if field_consumer_category(DocumentationPolicyConfig, field) == "LLM_ONLY"
    ]
    assert llm_only, "expected some LLM_ONLY documentation_policy fields to check"
    src_texts: dict[str, str] = {
        str(p): p.read_text(encoding="utf-8")
        for p in SRC_ROOT.rglob("*.py")
    }
    leaked: list[str] = []
    for field in llm_only:
        pattern = re.compile(
            r"(?:\." + re.escape(field) + r"\b|\[\s*['\"]" + re.escape(field) + r"['\"]\s*\])"
        )
        # config.py itself is where the field is declared — exclude it.
        for path, text in src_texts.items():
            if path.endswith("config.py"):
                continue
            if pattern.search(text):
                leaked.append(field)
                break
    assert not leaked, (
        "LLM_ONLY documentation_policy fields are read in Python src/: "
        + ", ".join(sorted(leaked))
    )


def test_python_consumed_fields_are_referenced_in_source():
    """Python-consumed fields must actually be read somewhere in ``src/``.

    This catches the most common drift: declaring a field ``Python-consumed``
    on the config model but never wiring it into a stage. The contract test
    then fails fast instead of letting dead config ship.
    """
    python_paths = python_consumed_field_paths()
    src_texts: dict[str, str] = {}
    for src_file in SRC_ROOT.rglob("*.py"):
        src_texts[str(src_file)] = src_file.read_text(encoding="utf-8")

    missing: list[str] = []
    for dotted in python_paths:
        # The last segment is the actual attribute name (handle dotted inner
        # attributes like ``scan.source_intelligence_max_files``).
        _, _, attr = dotted.rpartition(".")
        # Build a search pattern that matches the attribute name appearing as
        # a normal identifier (``.attr`` or ``["attr"]``).
        # We accept either attribute access or dict key access.
        pattern = re.compile(
            r"(?:\." + re.escape(attr) + r"\b|\[\s*['\"]" + re.escape(attr) + r"['\"]\s*\])"
        )
        if not any(pattern.search(text) for text in src_texts.values()):
            missing.append(dotted)
    assert not missing, (
        "Fields marked Python-consumed but never referenced in src/: " + ", ".join(missing)
    )


def test_yaml_config_templates_annotate_consumption():
    """Each field in the bundled config templates is annotated Python vs LLM.

    The annotation may appear either as ``# Python-consumed`` / ``# LLM-consumed``
    (or the SHARED form, which is read by both planes) on the field line itself,
    or as a section/block comment on the most recent preceding ``#``-prefixed
    line at the same or shallower indentation. Anything left unannotated means
    it drifted out of the consumption contract.
    """
    # SHARED is a first-class consumption category (Python validator + LLM
    # writer); it is accepted alongside ``Python-consumed`` / ``LLM-consumed``.
    # ``Legacy-consumed`` marks fields read only by the deprecated
    # ``legacy-generate`` / ``generate`` scaffold.
    VALID_ANNOTATIONS = ("Python-consumed", "LLM-consumed", "SHARED", "Legacy-consumed")
    template_paths = [
        PROJECT_ROOT / "templates" / "config.yaml",
        PROJECT_ROOT / "subskills" / "init" / "templates" / "default.config.yaml",
    ]
    missing: list[str] = []
    for path in template_paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for model_name, fields in _all_config_field_paths().items():
            for field in fields:
                if field == "target_dir":
                    continue  # runtime-only
                # If the field appears as a YAML key, require an annotation
                # either on the line itself (trailing comment) or on the most
                # recent preceding ``#``-prefixed block comment at the same
                # indent or shallower.
                pattern = re.compile(
                    r"(?:^|\n)(?P<indent>\s*)(?P<key>" + re.escape(field) + r"\s*:)(?P<rest>[^\n]*)",
                )
                match = pattern.search(text)
                if not match:
                    continue
                start = match.start()
                indent_len = len(match.group("indent"))
                rest = match.group("rest") or ""
                annotations: list[str] = []
                if any(tok in rest for tok in VALID_ANNOTATIONS):
                    annotations.append(rest)
                preceding = text[:start]
                for line in reversed(preceding.splitlines()):
                    stripped = line.lstrip()
                    line_indent = len(line) - len(stripped)
                    if not stripped:
                        continue
                    if stripped.startswith("#"):
                        # Block comments apply to siblings at *this* or shallower indent.
                        if line_indent <= indent_len:
                            annotations.append(stripped)
                            break
                        continue
                    break
                joined = "\n".join(annotations)
                if not any(tok in joined for tok in VALID_ANNOTATIONS):
                    missing.append(f"{path.relative_to(PROJECT_ROOT)}:{field} lacks consumer annotation")
    assert not missing, "\n".join(missing)


def test_python_consumed_field_subset_is_nonempty():
    """At least *some* fields are Python-consumed — guard against all-LLM regression."""
    assert len(python_consumed_field_paths()) > 0
    assert len(llm_consumed_field_paths()) > 0


def test_semantic_content_fields_are_legacy_only_not_python_only():
    """The LLM-first boundary: page-presence, uncertainty, and revision fields
    that control SEMANTIC authoring must be LEGACY_ONLY, never PYTHON_ONLY.

    ``generate_faq`` / ``generate_troubleshooting`` / ``generate_env_vars_page``
    decide whether Python emits semantic-content pages; ``emit_uncertainty_notes``
    and ``revision.*`` decide whether Python attaches uncertainty/revision prose.
    Those decisions belong to the LLM in the authoritative ``/makewiki`` flow, so
    Python may only consume them inside the deprecated legacy scaffold
    (LEGACY_ONLY). If one of these ever becomes PYTHON_ONLY, Python's "mechanical
    enforcement" surface would be silently authoring semantics — a boundary
    violation this contract must keep failing until it is classified legacy.
    """
    semantic_fields = {
        "MakeWikiConfig.generate_faq",
        "MakeWikiConfig.generate_troubleshooting",
        "MakeWikiConfig.generate_env_vars_page",
        "MakeWikiConfig.emit_uncertainty_notes",
        "RevisionConfig.enabled",
        "RevisionConfig.max_rounds",
        "RevisionConfig.auto_hedge_ungrounded",
        "RevisionConfig.auto_harmonize_code_blocks",
        "RevisionConfig.stop_on_no_progress",
    }
    categories = all_field_categories()
    for path in semantic_fields:
        assert categories[path] == "LEGACY_ONLY", (
            f"{path} must be LEGACY_ONLY (consumed only by the deprecated "
            f"legacy scaffold, never as authoritative Python semantics); "
            f"got {categories[path]}"
        )
    # The legacy scaffold must actually have a live surface (non-empty), else
    # LEGACY_ONLY is a fiction.
    assert len(legacy_consumed_field_paths()) > 0


def test_strict_grounding_and_write_policy_are_legacy_only_in_python_plane():
    """Python-only enforcement fields that are actually read ONLY by the legacy
    pipeline (strict_grounding, overwrite, delete_stale_files) must be LEGACY_ONLY.
    """
    categories = all_field_categories()
    for path in (
        "MakeWikiConfig.strict_grounding",
        "MakeWikiConfig.overwrite",
        "MakeWikiConfig.delete_stale_files",
        "MakeWikiConfig.revision",
    ):
        assert categories[path] == "LEGACY_ONLY", (
            f"{path} must be LEGACY_ONLY (read only by the legacy pipeline); "
            f"got {categories[path]}"
        )


def test_authoritative_output_fields_stay_python_only():
    """Fields read by the authoritative mechanical CLI (verify-docs / parity /
    review) stay PYTHON_ONLY — they are genuinely Python-mechanical."""
    categories = all_field_categories()
    for path in (
        "MakeWikiConfig.output_dir",
        "MakeWikiConfig.languages",
        "MakeWikiConfig.default_language",
    ):
        assert categories[path] == "PYTHON_ONLY", (
            f"{path} must stay PYTHON_ONLY (read by the authoritative CLI); "
            f"got {categories[path]}"
        )


def _authoritative_skill_text() -> str:
    """Concatenated SKILL.md + every tasks/*.md — the authoritative LLM layer."""
    parts: list[str] = []
    skill = PROJECT_ROOT / "SKILL.md"
    if skill.is_file():
        parts.append(skill.read_text(encoding="utf-8"))
    tasks_dir = PROJECT_ROOT / "tasks"
    for p in sorted(tasks_dir.glob("*.md")):
        parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_llm_only_fields_are_referenced_in_authoritative_skill_layer():
    """BEHAVIORAL LLM-consumption contract: every LLM_ONLY field must be
    genuinely consumed by the authoritative Skill layer — referenced by name in
    ``SKILL.md`` or a ``tasks/*.md`` task — not merely classified LLM_ONLY in
    ``config.py``.

    A field marked LLM-only that no writer / orchestrator instruction reads is
    dead config masked by category (the governance failure this contract
    exists to prevent). This positive check complements the negative test
    ``test_llm_only_fields_are_not_python_read``: it proves there is a real
    LLM-side reader, not just the absence of a Python read.
    """
    llm_only = [
        path for path, cat in all_field_categories().items() if cat == "LLM_ONLY"
    ]
    assert llm_only, "expected some LLM_ONLY fields to check"
    joined = _authoritative_skill_text()

    missing: list[str] = []
    for dotted in llm_only:
        attr = dotted.rpartition(".")[2]
        if not re.search(r"\b" + re.escape(attr) + r"\b", joined):
            missing.append(dotted)
    assert not missing, (
        "LLM_ONLY fields never referenced in the authoritative Skill layer "
        "(SKILL.md / tasks/*.md) — dead config masked by category: "
        + ", ".join(sorted(missing))
    )


def test_authoritative_audit_loop_is_budgeted_by_agent_max_audit_rounds():
    """GOVERNANCE: the authoritative ``/makewiki`` Auditor loop (SKILL.md) is
    bounded by the LLM-owned ``agent.max_audit_rounds``, NEVER by the legacy
    ``revision.max_rounds``.

    Regression guard against req-2-style failure: the legacy ``revision.*``
    block is LEGACY_ONLY (drives only the deprecated scaffold) and must not
    masquerade as authoritative orchestration. ``agent.max_audit_rounds`` must
    appear in SKILL.md, and ``revision.max_rounds`` must NOT appear anywhere in
    the authoritative Skill layer (SKILL.md / tasks/*.md).
    """
    skill = (PROJECT_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"\bmax_audit_rounds\b", skill), (
        "agent.max_audit_rounds must bound the authoritative Auditor loop in SKILL.md"
    )
    joined = _authoritative_skill_text()
    assert not re.search(r"revision\.max_rounds", joined), (
        "revision.max_rounds must NOT steer the authoritative /makewiki flow "
        "(SKILL.md / tasks/*.md); use agent.max_audit_rounds instead"
    )


def test_review_review_pair_toggle_is_mechanical_and_legacy_field_stays_gone():
    """REQ 9 + REQ 2 regression guard.

    ``review.enable_review_pair_generation`` is the MECHANICAL toggle for the
    ``semantic-review`` preparation command — the old name,
    ``review.enable_semantic_review``, is gone. And no ``revision.max_rounds``
    reference drives the authoritative loop (legacy field stays LEGACY_ONLY).
    """
    categories = all_field_categories()
    assert "ReviewConfig.enable_review_pair_generation" in categories
    assert categories["ReviewConfig.enable_review_pair_generation"] == "PYTHON_ONLY"
    assert "ReviewConfig.enable_semantic_review" not in categories, (
        "enable_semantic_review was renamed to enable_review_pair_generation so "
        "the name cannot imply closing the authoritative LLM semantic audit"
    )


def test_removed_dead_llm_only_field_is_gone():
    """``scan.max_external_urls`` was removed: it had no consumer and no fetch
    step (only a futures-planning comment), so keeping it LLM_ONLY was dead
    config masked by category. Regression guard that it stays gone."""
    declared = _all_config_field_paths()
    assert "max_external_urls" not in declared["ScanConfig"], (
        "scan.max_external_urls is dead config (no consumer, no fetch step) and "
        "must stay removed"
    )
