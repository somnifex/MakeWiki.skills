"""Project-level configuration model.

Every public field of :class:`MakeWikiConfig` maps to exactly one consumer
category — a field is never dead and is never ambiguous about who consumes it:

* ``PYTHON_ONLY`` — read by the mechanical Python plane only.
* ``LLM_ONLY`` — read by the Skill orchestrator / language writers only.
* ``SHARED`` — read by BOTH Python (mechanical enforcement) and the LLM
  (writing guidance). Example: ``documentation_policy.banned_descriptors`` is
  enforced by the Python validator and is also consulted by the writer to avoid
  banned descriptors.
* ``LEGACY_ONLY`` — only consumed by the deprecated ``legacy-generate`` /
  ``generate`` path: the ``LegacyDeterministicRenderer`` and the legacy
  ``Pipeline`` (revision engine, output manager). These fields control
  *semantic* scaffolding decisions (whether to emit faq/troubleshooting/
  env-vars pages, whether to attach uncertainty hedges, revision rounds) that
  the deprecated scaffold performs in Python. The authoritative ``/makewiki``
  flow never consults them — the LLM writers decide what to author. They are
  marked LEGACY_ONLY, not PYTHON_ONLY, so the contract knows Python consumes
  them only inside the non-authoritative scaffold, and they never leak into the
  authoritative plane's "Python mechanically enforces this" surface.

Config classes declare their membership across four ClassVars:

* ``_PYTHON_CONSUMED_FIELDS``: read by Python code paths (mechanical plane).
* ``_LLM_CONSUMED_FIELDS``: read by the Skill layer / writers only.
* ``_SHARED_CONSUMED_FIELDS``: read by both Python and the LLM.
* ``_LEGACY_CONSUMED_FIELDS``: read only by the legacy path (usually empty).

The contract test ``tests/contracts/test_config_consumption_contract.py``
enforces that **no public field is UNKNOWN** — every attribute must resolve to
exactly one of the four categories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Literal, cast, get_args

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

#: Every public config field maps to exactly one consumer category.
ConsumerCategory = Literal["PYTHON_ONLY", "LLM_ONLY", "SHARED", "LEGACY_ONLY"]

_CONSUMER_CATEGORIES: frozenset[str] = frozenset(get_args(ConsumerCategory))


class ScanConfig(BaseModel):
    """Controls which files and directories are scanned."""

    mode: str = "auto"  # "quick" | "standard" | "deep" | "auto"
    ignore_dirs: list[str] = Field(
        default_factory=lambda: [
            "node_modules",
            "dist",
            "build",
            ".git",
            ".makewiki",
            "__pycache__",
            ".venv",
            "venv",
        ]
    )
    max_depth: int = 6
    max_file_size_kb: int = 512
    enable_source_intelligence: bool = True
    source_intelligence_max_files: int = 50
    recursive_docs: bool = True

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "mode",
            "ignore_dirs",
            "max_depth",
            "max_file_size_kb",
            "enable_source_intelligence",
            "source_intelligence_max_files",
            "recursive_docs",
        }
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class ReviewConfig(BaseModel):
    """Controls cross-language and grounding review behaviour.

    ``enable_review_pair_generation`` (formerly ``enable_semantic_review``)
    is a MECHANICAL toggle: it gates whether the ``semantic-review`` CLI
    prepares aligned passage pairs for the LLM to review. It does NOT control
    the authoritative ``/makewiki`` LLM semantic audit — Python never closes
    that audit; the Auditor always runs over L3/L4b/L5 in the Skill layer.
    It was renamed so the name can never be misread as toggling the LLM
    semantic audit off.
    """

    enable_cross_language_review: bool = True
    enable_code_grounding_verification: bool = True
    enable_codebase_verification: bool = True
    enable_review_pair_generation: bool = True
    min_page_alignment_ratio: float = 0.9

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "enable_cross_language_review",
            "enable_code_grounding_verification",
            "enable_codebase_verification",
            "enable_review_pair_generation",
            "min_page_alignment_ratio",
        }
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class RevisionConfig(BaseModel):
    """Controls automatic document revision after verification."""

    enabled: bool = True

    # 最多修几轮，防止死循环
    max_rounds: int = Field(default=2, ge=0, le=5)

    # 对无法确认的命令是否添加 uncertainty
    auto_hedge_ungrounded: bool = True

    # 是否自动修复多语言 code block 不一致
    auto_harmonize_code_blocks: bool = True

    # 一轮 revision 没产生任何修改时停止
    stop_on_no_progress: bool = True

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    # The entire revision engine is the deprecated legacy scaffold. These fields
    # drive the legacy Pipeline's MechanicalRepairEngine loop (auto-hedge /
    # auto-harmonize are Python-authored semantic edits) and are therefore
    # LEGACY_ONLY — never part of the authoritative /makewiki plane.
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "enabled",
            "max_rounds",
            "auto_hedge_ungrounded",
            "auto_harmonize_code_blocks",
            "stop_on_no_progress",
        }
    )


class ContentDepthConfig(BaseModel):
    """Controls how much detail is generated and when pages are split into sub-pages."""

    mode: str = "auto"  # "compact" | "detailed" | "auto"
    max_faq_items: int = 20
    max_usage_examples: int = 8
    max_troubleshooting_items: int = 8
    split_usage_threshold: int = 6  # split usage into sub-pages when commands exceed this

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "mode",
            "max_faq_items",
            "max_usage_examples",
            "max_troubleshooting_items",
            "split_usage_threshold",
        }
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class DocumentationPolicyConfig(BaseModel):
    """Controls how conservative and user-facing the generated docs should be."""

    audience: str = "end-user"
    structure_strategy: str = "user-journey"
    prefer_task_oriented_sections: bool = True
    include_architecture_analysis: bool = False
    include_directory_overview: bool = False
    include_source_walkthroughs: bool = False
    forbid_unfounded_praise: bool = True
    banned_descriptors: list[str] = Field(
        default_factory=lambda: [
            "powerful",
            "robust",
            "flexible",
            "enterprise-grade",
            "high-performance",
            "elegant",
            "state-of-the-art",
            "cutting-edge",
            "seamless",
            "blazing-fast",
            "world-class",
            "best-in-class",
            "production-ready",
        ]
    )

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "audience",
            "structure_strategy",
            "prefer_task_oriented_sections",
            "include_architecture_analysis",
            "include_directory_overview",
            "include_source_walkthroughs",
        }
    )
    # Read by Python (renderer/validator.py enforces banned descriptors and the
    # no-unfounded-praise rule mechanically) AND consulted by the LLM writer as
    # writing guidance. Because ``forbid_unfounded_praise`` gates the ban, both
    # fields are SHARED.
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"banned_descriptors", "forbid_unfounded_praise"}
    )
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class LanguageProfileConfig(BaseModel):
    """Per-language overrides in the config file."""

    tone: str = "concise-user-facing"

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset({"tone"})
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class AgentConfig(BaseModel):
    """Controls multi-agent execution and subagent budget.

    ``max_audit_rounds`` is the AUTHORITATIVE budget for the Auditor's
    self-healing loop in ``/makewiki`` Phase 4: it bounds how many times the
    Auditor may re-run ``verify-docs --semantic-audit`` to resolve pending /
    failed L-layers before the loop stops. It is consumed by the LLM
    orchestrator only — Python never enforces it (the Quality Gate is a single
    decision point, not a loop). It deliberately replaces the legacy
    ``revision.max_rounds`` for the authoritative loop; the legacy field stays
    LEGACY_ONLY for the deprecated scaffold.
    """

    max_subagents: int = 10
    rebattle_rounds: int = 2
    max_audit_rounds: int = 3
    tier_override: str = "auto"  # "auto" | "S" | "M" | "L"

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"max_subagents", "rebattle_rounds", "max_audit_rounds", "tier_override"}
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class SiteConfig(BaseModel):
    """Controls static HTML website compilation."""

    compile: bool = True
    theme: str = "auto"  # "auto" | "light" | "dark"
    include_search: bool = True
    output_subdir: str = "site"

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"compile", "theme", "include_search", "output_subdir"}
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class DeliveryConfig(BaseModel):
    """Controls enterprise and commercial delivery documentation structure."""

    audience: str = "dual"  # "dual" | "end-user" | "enterprise"
    include_deployment_runbook: bool = True
    include_compatibility_matrix: bool = True
    include_health_checks: bool = True

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "audience",
            "include_deployment_runbook",
            "include_compatibility_matrix",
            "include_health_checks",
        }
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class QualityConfig(BaseModel):
    """Thresholds for the unified L0-L5 Quality Gate."""

    # When True, unresolved LLM-judged layers (L3/L4-prose/L5) that are left
    # pending do not by themselves fail the gate.
    allow_pending_llm_layers: bool = True
    # The single Quality Gate grounding threshold. This is the ONLY place the
    # gate reads a grounding score threshold — the revision engine no longer
    # carries its own copy.
    min_grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"allow_pending_llm_layers", "min_grounding_score"}
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class MakeWikiConfig(BaseModel):
    """Root configuration for a makewiki run."""

    output_dir: str = "makewiki"
    languages: list[str] = Field(default_factory=lambda: ["en", "zh-CN"])
    default_language: str = "en"
    overwrite: bool = True
    delete_stale_files: bool = False
    generate_faq: bool = True
    generate_troubleshooting: bool = True
    generate_env_vars_page: bool = True
    strict_grounding: bool = True
    emit_uncertainty_notes: bool = True
    scan: ScanConfig = Field(default_factory=ScanConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    revision: RevisionConfig = Field(default_factory=RevisionConfig)
    content_depth: ContentDepthConfig = Field(default_factory=ContentDepthConfig)
    documentation_policy: DocumentationPolicyConfig = Field(
        default_factory=DocumentationPolicyConfig
    )
    agent: AgentConfig = Field(default_factory=AgentConfig)
    site: SiteConfig = Field(default_factory=SiteConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    language_profiles: dict[str, LanguageProfileConfig] = Field(default_factory=dict)

    target_dir: Path = Field(default=Path("."))

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "output_dir",
            "languages",
            "default_language",
            "scan",
            "review",
            "quality",
            "site",
            "documentation_policy",
            "target_dir",
        }
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"agent", "delivery", "content_depth", "language_profiles"}
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    # These fields ONLY drive the deprecated ``legacy-generate`` / ``generate``
    # scaffold (the ``LegacyDeterministicRenderer`` emitting faq/troubleshooting/
    # env-vars pages and uncertainty notes, the legacy ``Pipeline`` write stage
    # and its ``CodeGroundingVerifier`` strictness, and the whole legacy revision
    # block). The authoritative ``/makewiki`` flow never reads them — the LLM
    # writers decide page composition and hedging. So they are LEGACY_ONLY, not
    # PYTHON_ONLY: Python consumes them only inside the non-authoritative
    # scaffold, and they must never appear as legitimate mechanical enforcement.
    _LEGACY_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "generate_faq",
            "generate_troubleshooting",
            "generate_env_vars_page",
            "strict_grounding",
            "emit_uncertainty_notes",
            "overwrite",
            "delete_stale_files",
            "revision",
        }
    )

    @classmethod
    def load(cls, config_path: Path, target_dir: Path | None = None) -> MakeWikiConfig:
        """Load from a YAML file, falling back to defaults for missing keys."""
        data: dict[str, Any] = {}
        config_path = Path(config_path)
        if config_path.is_file():
            raw = config_path.read_text(encoding="utf-8")
            data = cast(dict[str, Any], yaml.safe_load(raw) or {})
        cfg = cls.model_validate(data)
        if target_dir is not None:
            cfg.target_dir = Path(target_dir).resolve()
        return cfg

    @classmethod
    def default(cls, target_dir: Path | None = None) -> MakeWikiConfig:
        cfg = cls()
        if target_dir is not None:
            cfg.target_dir = Path(target_dir).resolve()
        return cfg

    def to_yaml(self) -> str:
        """Serialise to YAML (excludes runtime-only fields)."""
        data = self.model_dump(exclude={"target_dir"})
        return str(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))


def iter_config_models() -> list[type[BaseModel]]:
    """Return every config model class for contract-walking."""
    return [
        MakeWikiConfig,
        ScanConfig,
        ReviewConfig,
        RevisionConfig,
        ContentDepthConfig,
        DocumentationPolicyConfig,
        LanguageProfileConfig,
        AgentConfig,
        SiteConfig,
        DeliveryConfig,
        QualityConfig,
    ]


def python_consumed_field_paths() -> set[str]:
    """Return every field path read by Python — PYTHON_ONLY plus SHARED.

    A SHARED field is consumed by Python as well as the LLM, so it must be
    included here for the "every Python-marked field is referenced" contract.
    """
    paths: set[str] = set()
    for model in iter_config_models():
        py: frozenset[str] = getattr(model, "_PYTHON_CONSUMED_FIELDS", frozenset())
        shared: frozenset[str] = getattr(model, "_SHARED_CONSUMED_FIELDS", frozenset())
        for field in py | shared:
            paths.add(f"{model.__name__}.{field}")
    return paths


def llm_consumed_field_paths() -> set[str]:
    """Return every field path read by the LLM — LLM_ONLY plus SHARED.

    A SHARED field is consumed by the LLM as well as Python, so it must be
    included here too.
    """
    paths: set[str] = set()
    for model in iter_config_models():
        llm: frozenset[str] = getattr(model, "_LLM_CONSUMED_FIELDS", frozenset())
        shared: frozenset[str] = getattr(model, "_SHARED_CONSUMED_FIELDS", frozenset())
        for field in llm | shared:
            paths.add(f"{model.__name__}.{field}")
    return paths


def legacy_consumed_field_paths() -> set[str]:
    """Return every field path consumed ONLY by the deprecated legacy scaffold.

    LEGACY_ONLY fields are read by Python only inside ``legacy-generate`` /
    ``generate`` (the ``LegacyDeterministicRenderer``, the legacy ``Pipeline``,
    the ``MechanicalRepairEngine``). They are deliberately excluded from
    ``python_consumed_field_paths()`` so the authoritative-plane contract does
    not treat them as legitimate mechanical enforcement — but they must still be
    covered so ``test_every_config_field_is_marked_consumed`` does not report
    them as dead.
    """
    paths: set[str] = set()
    for model in iter_config_models():
        legacy: frozenset[str] = getattr(model, "_LEGACY_CONSUMED_FIELDS", frozenset())
        for field in legacy:
            paths.add(f"{model.__name__}.{field}")
    return paths


def _field_category(model: type[BaseModel], field: str) -> ConsumerCategory:
    """Classify a single field into exactly one consumer category.

    Ordering is significant: membership in the explicit SHARED set wins over
    the PYTHON/LLM sets (a field may appear on both when it is genuinely
    consumed by both planes). Every public field is classified; a field in none
    of the four sets is a contract violation and is raised loudly rather than
    silently returned as an impossible UNKNOWN.
    """
    shared: frozenset[str] = getattr(model, "_SHARED_CONSUMED_FIELDS", frozenset())
    py: frozenset[str] = getattr(model, "_PYTHON_CONSUMED_FIELDS", frozenset())
    llm: frozenset[str] = getattr(model, "_LLM_CONSUMED_FIELDS", frozenset())
    legacy: frozenset[str] = getattr(model, "_LEGACY_CONSUMED_FIELDS", frozenset())
    if field in shared:
        return "SHARED"
    if field in py:
        return "PYTHON_ONLY"
    if field in llm:
        return "LLM_ONLY"
    if field in legacy:
        return "LEGACY_ONLY"
    raise ValueError(
        f"Config field {model.__name__}.{field} is not classified in any of "
        "the four consumer categories (PYTHON_ONLY/LLM_ONLY/SHARED/LEGACY_ONLY)."
    )


def field_consumer_category(model: type[BaseModel], field: str) -> ConsumerCategory:
    """Return the consumer category for one field on one config model.

    Returns one of ``"PYTHON_ONLY"``, ``"LLM_ONLY"``, ``"SHARED"``, or
    ``"LEGACY_ONLY"``. An unconsumed field is a contract violation and is
    reported via ``ValueError`` — there is no silent ``UNKNOWN`` state.
    """
    return _field_category(model, field)


def all_field_categories() -> dict[str, ConsumerCategory]:
    """Map every public field to its single consumer category.

    Keys are ``"<Class>.<field>"`` paths (e.g. ``DocumentationPolicyConfig.
    banned_descriptors``). Every public field must classify; an unconsumed one
    raises (see :func:`field_consumer_category`).
    """
    categories: dict[str, ConsumerCategory] = {}
    for model in iter_config_models():
        for field in model.model_fields:
            categories[f"{model.__name__}.{field}"] = _field_category(model, field)
    return categories
