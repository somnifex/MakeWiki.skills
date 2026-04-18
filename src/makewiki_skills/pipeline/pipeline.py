"""Artifact-first orchestration pipeline for MakeWiki."""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.orchestration import (
    EvidenceIndex,
    PageArtifactAssembler,
    RunLayout,
    RunState,
    RunStore,
    SemanticModelIndex,
)
from makewiki_skills.renderer.output_manager import OutputManager
from makewiki_skills.renderer.validator import OutputValidator, ValidationReport
from makewiki_skills.review.cross_language_reviewer import (
    CrossLanguageReview,
    CrossLanguageReviewer,
)
from makewiki_skills.scanner.evidence_collector import CollectedEvidence, EvidenceCollector
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectDetector
from makewiki_skills.scanner.project_detector import ProjectType
from makewiki_skills.verification.code_grounding_verifier import (
    CodeGroundingVerifier,
    GroundingReport,
)
from makewiki_skills.verification.codebase_verifier import (
    CodebaseVerificationReport,
    CodebaseVerifier,
)


class PipelineContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: MakeWikiConfig

    detection: ProjectDetectionResult | None = None
    collected_evidence: CollectedEvidence | None = None
    evidence_registry: EvidenceRegistry = Field(default_factory=EvidenceRegistry)
    scan_fallback_required: bool = False
    scan_failure_reason: str | None = None
    run_layout: RunLayout | None = None
    state: RunState | None = None
    evidence_index: EvidenceIndex | None = None
    semantic_index: SemanticModelIndex | None = None
    generated_documents: dict[str, list[GeneratedDocument]] = Field(default_factory=dict)
    final_documents: dict[str, list[GeneratedDocument]] = Field(default_factory=dict)
    cross_language_review: CrossLanguageReview | None = None
    grounding_report: GroundingReport | None = None
    codebase_verification_report: CodebaseVerificationReport | None = None
    validation_report: ValidationReport | None = None

    stage_timings: dict[str, float] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    written_files: list[str] = Field(default_factory=list)


def stage_detect_project(ctx: PipelineContext) -> PipelineContext:
    detector = ProjectDetector()
    try:
        ctx.detection = detector.detect(ctx.config.target_dir)
    except Exception as exc:
        if not ctx.config.scan.allow_llm_fallback_on_failure:
            ctx.errors.append(f"Cannot detect project: {exc}")
            return ctx
        ctx.scan_fallback_required = True
        ctx.scan_failure_reason = f"Project detection failed: {exc}"
        ctx.warnings.append(
            f"Python project detection failed; falling back to LLM scan: {exc}"
        )
        ctx.detection = ProjectDetectionResult(
            project_type=ProjectType.GENERIC,
            confidence=0.0,
            project_name=ctx.config.target_dir.resolve().name,
            project_dir=str(ctx.config.target_dir.resolve()),
        )
    return ctx


def stage_collect_evidence(ctx: PipelineContext) -> PipelineContext:
    if ctx.detection is None:
        ctx.errors.append("Cannot collect evidence: no detection result")
        return ctx

    collector = EvidenceCollector(ctx.config)
    try:
        ctx.collected_evidence = collector.collect(ctx.config.target_dir, ctx.detection)
        if ctx.scan_fallback_required and ctx.collected_evidence.fallback_reason is None:
            ctx.collected_evidence.fallback_reason = ctx.scan_failure_reason
        ctx.evidence_registry.add_many(ctx.collected_evidence.facts)
    except Exception as exc:
        if not ctx.config.scan.allow_llm_fallback_on_failure:
            ctx.errors.append(f"Cannot collect evidence: {exc}")
            return ctx
        ctx.scan_fallback_required = True
        if ctx.scan_failure_reason:
            ctx.scan_failure_reason = f"{ctx.scan_failure_reason}; evidence collection failed: {exc}"
        else:
            ctx.scan_failure_reason = str(exc)
        ctx.warnings.append(
            f"Python evidence scan failed; LLM scan fallback is required: {exc}"
        )
        ctx.collected_evidence = CollectedEvidence(
            project_dir=str(ctx.config.target_dir.resolve()),
            detection=ctx.detection,
            collection_mode="llm-fallback",
            fallback_reason=ctx.scan_failure_reason,
        )
    return ctx


def stage_prepare_run(ctx: PipelineContext) -> PipelineContext:
    if ctx.detection is None or ctx.collected_evidence is None:
        ctx.errors.append("Cannot prepare run: missing detection or evidence")
        return ctx

    store = RunStore(ctx.config)
    layout, state, evidence_index, resumed, _planned_files = store.prepare_run(
        ctx.detection,
        ctx.collected_evidence,
    )
    ctx.run_layout = layout
    ctx.state = state
    ctx.evidence_index = evidence_index
    if resumed:
        ctx.warnings.append(f"Resumed existing run {layout.run_id}")
    return ctx


def stage_refresh_state(ctx: PipelineContext) -> PipelineContext:
    if ctx.run_layout is None:
        ctx.errors.append("Cannot refresh state: no run layout")
        return ctx

    store = RunStore(ctx.config)
    ctx.state, ctx.semantic_index = store.refresh_state(ctx.run_layout, ctx.config.languages)
    ready_jobs = store.ready_jobs(ctx.state)
    if ready_jobs:
        ctx.warnings.append(f"{len(ready_jobs)} job(s) are ready for the LLM orchestrator")
    return ctx


def stage_assemble_output(ctx: PipelineContext) -> PipelineContext:
    if ctx.run_layout is None or ctx.state is None:
        ctx.errors.append("Cannot assemble output: run is not prepared")
        return ctx

    store = RunStore(ctx.config)
    assembler = PageArtifactAssembler(ctx.config)
    documents, warnings = assembler.assemble(ctx.run_layout, store)
    ctx.warnings.extend(warnings)
    ctx.generated_documents = documents
    ctx.final_documents = documents

    if not any(documents.values()):
        return ctx

    output_dir = ctx.config.target_dir / ctx.config.output_dir
    manager = OutputManager(
        output_dir,
        overwrite=ctx.config.overwrite,
        delete_stale_files=ctx.config.delete_stale_files,
    )
    written = manager.write_documents(documents)
    manager.write_index(documents, ctx.config.default_language)
    ctx.written_files = [str(path) for path in written]
    return ctx


def stage_cross_language_review(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.review.enable_cross_language_review:
        return ctx
    if len([lang for lang, docs in ctx.final_documents.items() if docs]) < 2:
        return ctx

    reviewer = CrossLanguageReviewer()
    ctx.cross_language_review = reviewer.review(ctx.final_documents)
    return ctx


def stage_grounding_verification(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.review.enable_code_grounding_verification:
        return ctx
    if not any(ctx.final_documents.values()):
        return ctx

    verifier = CodeGroundingVerifier(
        ctx.evidence_registry,
        strict=ctx.config.strict_grounding,
    )
    ctx.grounding_report = verifier.verify(ctx.final_documents)
    return ctx


def stage_codebase_verification(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.review.enable_codebase_verification:
        return ctx
    if not any(ctx.final_documents.values()):
        return ctx

    verifier = CodebaseVerifier(ctx.config.target_dir)
    ctx.codebase_verification_report = verifier.verify(ctx.final_documents)
    return ctx


def stage_validate_output(ctx: PipelineContext) -> PipelineContext:
    output_dir = ctx.config.target_dir / ctx.config.output_dir
    if not output_dir.is_dir():
        return ctx

    validator = OutputValidator(ctx.config.documentation_policy)
    ctx.validation_report = validator.validate(output_dir)
    return ctx


STAGES = [
    ("detect_project", stage_detect_project),
    ("collect_evidence", stage_collect_evidence),
    ("prepare_run", stage_prepare_run),
    ("refresh_state", stage_refresh_state),
    ("assemble_output", stage_assemble_output),
    ("cross_language_review", stage_cross_language_review),
    ("grounding_verification", stage_grounding_verification),
    ("codebase_verification", stage_codebase_verification),
    ("validate_output", stage_validate_output),
]


class Pipeline:
    def __init__(self, config: MakeWikiConfig) -> None:
        self._config = config

    def run(self) -> PipelineContext:
        ctx = PipelineContext(config=self._config)
        for name, stage_fn in STAGES:
            start = time.monotonic()
            ctx = stage_fn(ctx)
            ctx.stage_timings[name] = round(time.monotonic() - start, 3)
        return ctx

    def run_until(self, stage_name: str) -> PipelineContext:
        ctx = PipelineContext(config=self._config)
        for name, stage_fn in STAGES:
            start = time.monotonic()
            ctx = stage_fn(ctx)
            ctx.stage_timings[name] = round(time.monotonic() - start, 3)
            if name == stage_name:
                break
        return ctx
