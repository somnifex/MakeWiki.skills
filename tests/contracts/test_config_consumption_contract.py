"""Config Consumption Contract: every MakeWikiConfig field is consumed.

This contract enforces the Two-Plane invariant:
> Every field in ``makewiki.config.yaml`` is either Python-consumed
> (mechanical plane), LLM-consumed (Skill orchestrator / writers), or SHARED.
> No field is dead, and no legacy field remains.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from makewiki_skills.config import (
    RUNTIME_ONLY_FIELDS,
    DocumentationPolicyConfig,
    MakeWikiConfig,
    ReviewConfig,
    all_field_categories,
    field_consumer_category,
    iter_config_models,
    llm_consumed_field_paths,
    python_consumed_field_paths,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"


def _all_config_field_paths() -> dict[str, set[str]]:
    """Map each config class to its declared (non-ClassVar) attribute names,
    excluding runtime-only fields (e.g. ``target_dir``) that are not consumed."""
    fields: dict[str, set[str]] = {}
    for model in iter_config_models():
        names = set()
        for attr_name in model.model_fields:
            if f"{model.__name__}.{attr_name}" in RUNTIME_ONLY_FIELDS:
                continue
            names.add(attr_name)
        fields[model.__name__] = names
    return fields


def test_every_config_field_is_marked_consumed():
    """Union of Python + LLM consumed sets == every declared field."""
    declared = _all_config_field_paths()
    python_paths = python_consumed_field_paths()
    llm_paths = llm_consumed_field_paths()

    failures: list[str] = []
    for model_name, fields in declared.items():
        consumed_here = {
            p for p in python_paths | llm_paths
            if p.startswith(f"{model_name}.")
        }
        expected = {f"{model_name}.{f}" for f in fields}
        missing = expected - consumed_here
        if missing:
            failures.append(f"{model_name}: not classified consumed: {sorted(missing)}")
    assert not failures, "\n".join(failures)


def test_config_consumer_classification_complete():
    """Every public config field maps to EXACTLY ONE of the three categories:
    PYTHON_ONLY / LLM_ONLY / SHARED.
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

    # Every category is one of the three legal values.
    legal = {"PYTHON_ONLY", "LLM_ONLY", "SHARED"}
    illegal = {p for p, cat in categories.items() if cat not in legal}
    assert not illegal, "Field mapped to an illegal category: " + ", ".join(sorted(illegal))


def test_documentation_policy_judgment_fields_are_llm_only():
    """forbid_unfounded_praise / banned_descriptors are cognitive judgments the
    LLM writer plane consumes. With the mechanical prose checker removed from
    the validator (Python no longer decides prose quality), these fields are
    LLM_ONLY, not SHARED."""
    assert (
        field_consumer_category(DocumentationPolicyConfig, "forbid_unfounded_praise")
        == "LLM_ONLY"
    )
    assert (
        field_consumer_category(DocumentationPolicyConfig, "banned_descriptors")
        == "LLM_ONLY"
    )


def test_llm_only_fields_are_not_python_read():
    """LLM_ONLY documentation_policy fields are NOT consumed by Python."""
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


def test_python_consumed_fields_are_referenced_in_authoritative_source():
    """Python-consumed fields must actually be read somewhere in ``src/``."""
    python_paths = python_consumed_field_paths()
    src_texts: dict[str, str] = {
        str(src_file): src_file.read_text(encoding="utf-8")
        for src_file in SRC_ROOT.rglob("*.py")
    }
    if not src_texts:
        raise AssertionError("no source files to scan")

    missing: list[str] = []
    for dotted in python_paths:
        _, _, attr = dotted.rpartition(".")
        pattern = re.compile(
            r"(?:\." + re.escape(attr) + r"\b|\[\s*['\"]" + re.escape(attr) + r"['\"]\s*\])"
        )
        if not any(pattern.search(text) for text in src_texts.values()):
            missing.append(dotted)
    assert not missing, (
        "Fields marked Python-consumed but never referenced in src/: " + ", ".join(missing)
    )


def test_yaml_config_templates_annotate_consumption():
    """Each field in the bundled config templates is annotated Python vs LLM vs SHARED."""
    VALID_ANNOTATIONS = ("Python-consumed", "LLM-consumed", "SHARED")
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
                        if line_indent <= indent_len:
                            annotations.append(stripped)
                            break
                        continue
                    break
                joined = "\n".join(annotations)
                if not any(tok in joined for tok in VALID_ANNOTATIONS):
                    missing.append(f"{path.relative_to(PROJECT_ROOT)}:{field} lacks consumer annotation")
    assert not missing, "\n".join(missing)


def test_legacy_fields_are_completely_absent():
    """All legacy fields and models are deleted from config schema."""
    legacy_root_fields = {
        "generate_faq",
        "generate_troubleshooting",
        "generate_env_vars_page",
        "emit_uncertainty_notes",
        "strict_grounding",
        "overwrite",
        "delete_stale_files",
        "revision",
        "site",
    }
    present_root = legacy_root_fields & set(MakeWikiConfig.model_fields.keys())
    assert not present_root, f"Legacy fields must be removed from MakeWikiConfig: {present_root}"

    legacy_review_fields = {
        "enable_cross_language_review",
        "enable_code_grounding_verification",
        "enable_codebase_verification",
    }
    present_review = legacy_review_fields & set(ReviewConfig.model_fields.keys())
    assert not present_review, f"Legacy fields must be removed from ReviewConfig: {present_review}"


def test_config_models_reject_unknown_and_legacy_keys():
    """Every config model forbids unknown and legacy keys (extra='forbid')."""
    for model in iter_config_models():
        assert model.model_config.get("extra") == "forbid", (
            f"{model.__name__} must reject unknown keys (extra='forbid')"
        )

    # Legacy keys must raise ValidationError
    legacy_attempts = [
        {"generate_faq": True},
        {"generate_troubleshooting": True},
        {"revision": {"enabled": True}},
        {"site": {"compile": True}},
        {"overwrite": True},
        {"delete_stale_files": True},
        {"review": {"enable_codebase_verification": True}},
    ]
    for attempt in legacy_attempts:
        try:
            MakeWikiConfig.model_validate(attempt)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"Legacy payload {attempt} must fail validation with extra='forbid'")


def test_runtime_only_target_dir_is_excluded_from_consumption_contract():
    """target_dir is runtime state: never claimed consumed, never in categories."""
    assert "MakeWikiConfig.target_dir" in RUNTIME_ONLY_FIELDS
    assert "MakeWikiConfig.target_dir" not in python_consumed_field_paths()
    assert "MakeWikiConfig.target_dir" not in llm_consumed_field_paths()
    assert "MakeWikiConfig.target_dir" not in all_field_categories()


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
    """Every LLM_ONLY field is genuinely consumed by the authoritative Skill layer."""
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
        "LLM_ONLY fields never referenced in the authoritative Skill layer: "
        + ", ".join(sorted(missing))
    )


def test_authoritative_audit_loop_is_budgeted_by_agent_max_audit_rounds():
    """The authoritative /makewiki Auditor loop is bounded by agent.max_audit_rounds."""
    skill = (PROJECT_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(r"\bmax_audit_rounds\b", skill)
    joined = _authoritative_skill_text()
    assert not re.search(r"revision\.max_rounds", joined)
