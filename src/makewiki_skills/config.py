"""Project-level configuration model.

Every public field of :class:`MakeWikiConfig` maps to exactly one consumer
category — a field is never dead and is never ambiguous about who consumes it:

* ``PYTHON_ONLY`` — read by the mechanical Python plane only.
* ``LLM_ONLY`` — read by the Skill orchestrator / language writers only.
* ``SHARED`` — read by BOTH Python (mechanical enforcement) and the LLM
  (writing guidance). Example: ``documentation_policy.banned_descriptors`` is
  consulted by the writer to avoid banned descriptors. (No field is currently
  SHARED: with the mechanical validator prose checker removed, none of the
  documentation_policy prose-judgment fields is read by Python.)

Config classes declare their membership across three ClassVars:

* ``_PYTHON_CONSUMED_FIELDS``: read by Python code paths (mechanical plane).
* ``_LLM_CONSUMED_FIELDS``: read by the Skill layer / writers only.
* ``_SHARED_CONSUMED_FIELDS``: read by both Python and the LLM.

The contract test ``tests/contracts/test_config_consumption_contract.py``
enforces that **no public field is UNKNOWN** — every attribute must resolve to
exactly one of the three categories.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Literal, cast, get_args

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

#: Every public config field maps to exactly one consumer category.
ConsumerCategory = Literal["PYTHON_ONLY", "LLM_ONLY", "SHARED"]

_CONSUMER_CATEGORIES: frozenset[str] = frozenset(get_args(ConsumerCategory))

#: Config models reject unknown keys (``extra="forbid"``) so an unrecognised
#: field in ``makewiki.config.yaml`` fails loudly instead of being silently
#: discarded by pydantic's default ``extra="ignore"``. A silent-dead-field in
#: the YAML (a key with no backing model field and no consumer) is a contract
#: violation this prevents at load time, not just in a structural walk.
_STRICT_CONFIG = ConfigDict(extra="forbid")

#: Fields that are RUNTIME STATE rather than consumed configuration. They are
#: declared on a model (so callers may pass them as constructor kwargs and
#: ``default()``/``load()`` may write them) but are deliberately EXCLUDED from
#: the two-plane consumption contract: nobody reads them, so marking them
#: PYTHON_ONLY / LLM_ONLY / SHARED would be a lie.
RUNTIME_ONLY_FIELDS: frozenset[str] = frozenset({"MakeWikiConfig.target_dir"})


class ScanConfig(BaseModel):
    """Controls which files and directories are scanned."""

    model_config = _STRICT_CONFIG

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


class ReviewConfig(BaseModel):
    """Controls cross-language review and passage pair generation."""

    model_config = _STRICT_CONFIG

    enable_review_pair_generation: bool = True
    min_page_alignment_ratio: float = 0.9

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "enable_review_pair_generation",
            "min_page_alignment_ratio",
        }
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class ContentDepthConfig(BaseModel):
    """Controls how much detail is generated and when pages are split into sub-pages."""

    model_config = _STRICT_CONFIG

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


class DocumentationPolicyConfig(BaseModel):
    """Controls how conservative and user-facing the generated docs should be.

    ``audience`` is a **seed hint**, never a gate: it is a first guess handed to
    the Documentation Architect / Orientation, not the authoritative audience
    decision. In V3 the authoritative audience lives in the LLM-authored
    ``DocumentationModel.personas`` and per-page ``PageSpec.audience``
    (``references/v3/DOCUMENTATION_MODEL.md``, ``tasks/document-model.md``). The
    same re-scoping applies to ``delivery.audience``, which only biases
    *delivery-structure* (the ``include_*`` toggles), never general audience.

    ``include_operator_persona`` and ``include_api_reference`` are additive
    **seed switches**: when true they lower the threshold for the Architect to
    *look for* an operator persona / public-or-management API surface. They
    never manufacture a page or prose without evidence, and they never gate —
    operator/API coverage is still synthesized from evidence regardless.
    """

    model_config = _STRICT_CONFIG

    #: Seed persona hint for Orientation / Documentation Architect — the
    #: authoritative audience lives in DocumentationModel.personas + PageSpec.audience.
    audience: str = "end-user"
    structure_strategy: str = "user-journey"
    prefer_task_oriented_sections: bool = True
    include_architecture_analysis: bool = False
    include_directory_overview: bool = False
    include_source_walkthroughs: bool = False
    #: Seed switch: when True, explicitly run the operator checklist and consider
    #: an operator/admin reference. Evidence-gated; never forces operator docs.
    include_operator_persona: bool = False
    #: Seed switch: when True, Page Planning must look for public-API and/or
    #: management-API surfaces and, where proven, emit api_reference PageSpecs.
    #: Still evidence-gated — no surface, no page, even with the flag on.
    include_api_reference: bool = False
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
            "include_operator_persona",
            "include_api_reference",
            "forbid_unfounded_praise",
            "banned_descriptors",
        }
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class LanguageProfileConfig(BaseModel):
    """Per-language overrides in the config file."""

    model_config = _STRICT_CONFIG

    tone: str = "concise-user-facing"

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset({"tone"})
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class AgentConfig(BaseModel):
    """Controls multi-agent execution budget and safety resource limits.

    All fields are UPPER BOUNDS / SAFETY CEILINGS, not prescriptive execution
    plans. The LLM Orchestrator dynamically synthesizes SubtaskSpecs against the
    stable role families and determines loop termination (stopping as soon as
    facts converge), bounded by these caps. These fields are LLM-consumed budget
    hints only - Python never schedules subtasks or selects roles.
    """

    model_config = _STRICT_CONFIG

    max_subagents: int = Field(default=10, ge=1, le=20)
    max_parallelism: int = Field(default=10, ge=1, le=50)
    max_total_agent_calls: int | None = Field(default=None, ge=1)
    cost_budget: float | None = Field(default=None, ge=0.0)
    max_audit_rounds: int = Field(default=3, ge=1, le=10)
    safety_max_rounds: int = Field(default=3, ge=1, le=10)

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "max_subagents",
            "max_parallelism",
            "max_total_agent_calls",
            "cost_budget",
            "max_audit_rounds",
            "safety_max_rounds",
        }
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class DeliveryConfig(BaseModel):
    """Controls enterprise and commercial delivery documentation structure."""

    model_config = _STRICT_CONFIG

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


class QualityConfig(BaseModel):
    """Thresholds for the unified L0-L5 Quality Gate."""

    model_config = _STRICT_CONFIG

    # When True, unresolved LLM-judged layers (L3/L4-prose/L5) that are left
    # pending do not by themselves fail the gate.
    allow_pending_llm_layers: bool = True
    # The single Quality Gate grounding threshold. This is the ONLY place the
    # gate reads a grounding score threshold.
    min_grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"allow_pending_llm_layers", "min_grounding_score"}
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()


class MakeWikiConfig(BaseModel):
    """Root configuration for a makewiki run."""

    model_config = _STRICT_CONFIG

    output_dir: str = "makewiki"
    languages: list[str] = Field(default_factory=lambda: ["en", "zh-CN"])
    default_language: str = "en"
    scan: ScanConfig = Field(default_factory=ScanConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    content_depth: ContentDepthConfig = Field(default_factory=ContentDepthConfig)
    documentation_policy: DocumentationPolicyConfig = Field(
        default_factory=DocumentationPolicyConfig
    )
    agent: AgentConfig = Field(default_factory=AgentConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    language_profiles: dict[str, LanguageProfileConfig] = Field(default_factory=dict)

    # ``target_dir`` is RUNTIME STATE, not a consumed config field. It is the
    # resolved project directory a run was launched against, written by
    # :meth:`MakeWikiConfig.default` / :meth:`MakeWikiConfig.load`, excluded
    # from ``to_yaml`` serialisation, and never read back by any consumer.
    # It is kept a declared pydantic field only so callers may pass it as a
    # constructor kwarg; the consumption contract explicitly excludes it via
    # :data:`RUNTIME_ONLY_FIELDS` (a field nobody consumes must never be
    # claimed as consumed).
    target_dir: Path = Field(default=Path("."))

    _PYTHON_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "output_dir",
            "languages",
            "default_language",
            "scan",
            "review",
            "quality",
        }
    )
    _LLM_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"agent", "delivery", "content_depth", "documentation_policy", "language_profiles"}
    )
    _SHARED_CONSUMED_FIELDS: ClassVar[frozenset[str]] = frozenset()

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
        """Serialise to YAML (excludes runtime-only attributes like target_dir)."""
        data = self.model_dump()
        return str(yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False))


def iter_config_models() -> list[type[BaseModel]]:
    """Return every active config model class for contract-walking."""
    return [
        MakeWikiConfig,
        ScanConfig,
        ReviewConfig,
        ContentDepthConfig,
        DocumentationPolicyConfig,
        LanguageProfileConfig,
        AgentConfig,
        DeliveryConfig,
        QualityConfig,
    ]


def python_consumed_field_paths() -> set[str]:
    """Return every field path read by Python — PYTHON_ONLY plus SHARED.

    A SHARED field is consumed by Python as well as the LLM, so it must be
    included here for the "every Python-marked field is referenced" contract.
    Runtime-only fields are excluded (nobody reads them).
    """
    paths: set[str] = set()
    for model in iter_config_models():
        py: frozenset[str] = getattr(model, "_PYTHON_CONSUMED_FIELDS", frozenset())
        shared: frozenset[str] = getattr(model, "_SHARED_CONSUMED_FIELDS", frozenset())
        for field in py | shared:
            paths.add(f"{model.__name__}.{field}")
    return paths - RUNTIME_ONLY_FIELDS


def llm_consumed_field_paths() -> set[str]:
    """Return every field path read by the LLM — LLM_ONLY plus SHARED.

    A SHARED field is consumed by the LLM as well as Python, so it must be
    included here too. Runtime-only fields are excluded (nobody reads them).
    """
    paths: set[str] = set()
    for model in iter_config_models():
        llm: frozenset[str] = getattr(model, "_LLM_CONSUMED_FIELDS", frozenset())
        shared: frozenset[str] = getattr(model, "_SHARED_CONSUMED_FIELDS", frozenset())
        for field in llm | shared:
            paths.add(f"{model.__name__}.{field}")
    return paths - RUNTIME_ONLY_FIELDS


def _field_category(model: type[BaseModel], field: str) -> ConsumerCategory:
    """Classify a single field into exactly one consumer category.

    Ordering is significant: membership in the explicit SHARED set wins over
    the PYTHON/LLM sets (a field may appear on both when it is genuinely
    consumed by both planes). Every public *consumed* field is classified; a
    runtime-only field must be skipped by callers via
    :data:`RUNTIME_ONLY_FIELDS` before this is invoked, and a consumed field
    in none of the three sets is a contract violation raised loudly rather than
    silently returned as an impossible UNKNOWN.
    """
    shared: frozenset[str] = getattr(model, "_SHARED_CONSUMED_FIELDS", frozenset())
    py: frozenset[str] = getattr(model, "_PYTHON_CONSUMED_FIELDS", frozenset())
    llm: frozenset[str] = getattr(model, "_LLM_CONSUMED_FIELDS", frozenset())
    if field in shared:
        return "SHARED"
    if field in py:
        return "PYTHON_ONLY"
    if field in llm:
        return "LLM_ONLY"
    raise ValueError(
        f"Config field {model.__name__}.{field} is not classified in any of "
        "the three consumer categories (PYTHON_ONLY/LLM_ONLY/SHARED)."
    )


def field_consumer_category(model: type[BaseModel], field: str) -> ConsumerCategory:
    """Return the consumer category for one field on one config model.

    Returns one of ``"PYTHON_ONLY"``, ``"LLM_ONLY"``, or ``"SHARED"``. An
    unconsumed field is a contract violation and is reported via ``ValueError``.
    """
    return _field_category(model, field)


def all_field_categories() -> dict[str, ConsumerCategory]:
    """Map every public, consumed field to its single consumer category.

    Keys are ``"<Class>.<field>"`` paths (e.g. ``DocumentationPolicyConfig.
    banned_descriptors``). Runtime-only fields (``target_dir``) are excluded —
    nobody consumes them. Every remaining field must classify; an unconsumed
    one raises (see :func:`field_consumer_category`).
    """
    categories: dict[str, ConsumerCategory] = {}
    for model in iter_config_models():
        for field in model.model_fields:
            path = f"{model.__name__}.{field}"
            if path in RUNTIME_ONLY_FIELDS:
                continue
            categories[path] = _field_category(model, field)
    return categories
