"""Project-level configuration model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field


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
    max_external_urls: int = 3
    recursive_docs: bool = True


class ReviewConfig(BaseModel):
    """Controls cross-language and grounding review behaviour."""

    enable_cross_language_review: bool = True
    enable_code_grounding_verification: bool = True
    enable_codebase_verification: bool = True
    enable_semantic_review: bool = True
    min_page_alignment_ratio: float = 0.9


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

    # 最低 grounding 分数
    min_grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)


class ContentDepthConfig(BaseModel):
    """Controls how much detail is generated and when pages are split into sub-pages."""

    mode: str = "auto"  # "compact" | "detailed" | "auto"
    max_faq_items: int = 20
    max_usage_examples: int = 8
    max_troubleshooting_items: int = 8
    split_usage_threshold: int = 6  # split usage into sub-pages when commands exceed this


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


class LanguageProfileConfig(BaseModel):
    """Per-language overrides in the config file."""

    tone: str = "concise-user-facing"


class AgentConfig(BaseModel):
    """Controls multi-agent execution and subagent budget."""

    max_subagents: int = 10
    rebattle_rounds: int = 2
    tier_override: str = "auto"  # "auto" | "S" | "M" | "L"


class SiteConfig(BaseModel):
    """Controls static HTML website compilation."""

    compile: bool = True
    theme: str = "auto"  # "auto" | "light" | "dark"
    include_search: bool = True
    output_subdir: str = "site"


class DeliveryConfig(BaseModel):
    """Controls enterprise and commercial delivery documentation structure."""

    audience: str = "dual"  # "dual" | "end-user" | "enterprise"
    include_deployment_runbook: bool = True
    include_compatibility_matrix: bool = True
    include_health_checks: bool = True


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
    language_profiles: dict[str, LanguageProfileConfig] = Field(default_factory=dict)

    target_dir: Path = Field(default=Path("."))

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
