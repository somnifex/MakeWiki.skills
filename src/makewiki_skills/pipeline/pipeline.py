"""Orchestrate the documentation pipeline."""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import GeneratedDocument, LanguageGenerator
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.claim import (
    ClaimSet,
    build_claims_from_evidence,
    verify_claims_against_codebase,
)
from makewiki_skills.model.semantic_model import (
    Command,
    ConfigItem,
    ConfigSection,
    InstallStep,
    InstallationGuide,
    Prerequisite,
    ProjectIdentity,
    SemanticModel,
    SemanticModelProvenance,
)
from makewiki_skills.renderer.output_manager import OutputManager
from makewiki_skills.renderer.validator import OutputValidator, ValidationReport
from makewiki_skills.review.cross_language_reviewer import (
    CrossLanguageReview,
    CrossLanguageReviewer,
)
from makewiki_skills.revision.revision_engine import (
    RevisionEngine,
    RevisionReport,
)
from makewiki_skills.scanner.evidence_collector import CollectedEvidence, EvidenceCollector
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import (
    ProjectDetectionResult,
    ProjectDetector,
    ProjectType,
)
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink
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
    claim_set: ClaimSet | None = None
    semantic_model: SemanticModel | None = None
    generated_documents: dict[str, list[GeneratedDocument]] = Field(default_factory=dict)
    cross_language_review: CrossLanguageReview | None = None
    grounding_report: GroundingReport | None = None
    codebase_verification_report: CodebaseVerificationReport | None = None
    revision_reports: list[RevisionReport] = Field(default_factory=list)
    revision_rounds: int = 0
    revision_report: RevisionReport | None = None
    final_documents: dict[str, list[GeneratedDocument]] = Field(default_factory=dict)
    validation_report: ValidationReport | None = None

    stage_timings: dict[str, float] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    written_files: list[str] = Field(default_factory=list)


def stage_detect_project(ctx: PipelineContext) -> PipelineContext:
    detector = ProjectDetector()
    ctx.detection = detector.detect(ctx.config.target_dir)
    return ctx


def stage_collect_evidence(ctx: PipelineContext) -> PipelineContext:
    if ctx.detection is None:
        ctx.errors.append("Cannot collect evidence: no detection result")
        return ctx

    collector = EvidenceCollector(ctx.config)
    ctx.collected_evidence = collector.collect(ctx.config.target_dir, ctx.detection)
    ctx.evidence_registry.add_many(ctx.collected_evidence.facts)
    return ctx


def stage_build_claims(ctx: PipelineContext) -> PipelineContext:
    if ctx.detection is None:
        ctx.errors.append("Cannot build claims: no detection result")
        return ctx

    ctx.claim_set = build_claims_from_evidence(ctx.detection, ctx.evidence_registry)
    return ctx


def stage_verify_claims(ctx: PipelineContext) -> PipelineContext:
    if ctx.claim_set is None:
        ctx.errors.append("Cannot verify claims: no claim set")
        return ctx

    ctx.claim_set = verify_claims_against_codebase(ctx.claim_set, ctx.config.target_dir)
    return ctx


def stage_build_semantic_model(ctx: PipelineContext) -> PipelineContext:
    if ctx.detection is None or ctx.collected_evidence is None:
        ctx.errors.append("Cannot build model: missing detection or evidence")
        return ctx

    registry = ctx.evidence_registry
    identity = _build_identity(registry, ctx.detection)
    installation = _build_installation(registry, ctx.detection)
    configuration = _build_configuration(registry)
    commands = _build_commands(registry)

    # Cognitive content (user_tasks, usage_examples, faq, platform_notes,
    # troubleshooting, command_groups, env_vars, compatibility_matrix,
    # health_checks, deployment_notes, log_paths) is LLM-authored. This
    # deterministic scaffold intentionally leaves those fields empty and marks
    # them `unknown` rather than inventing semantic conclusions.
    provenance = SemanticModelProvenance(
        source="python" if commands or configuration else "unknown",
        identity="python",
        installation="python" if installation.evidence or installation.prerequisites else "unknown",
        configuration="python" if configuration else "unknown",
        commands="python" if commands else "unknown",
    )

    ctx.semantic_model = SemanticModel(
        model_id=uuid.uuid4().hex[:12],
        provenance=provenance,
        identity=identity,
        installation=installation,
        configuration=configuration,
        commands=commands,
        project_type=ctx.detection.project_type,
        evidence_summary=registry.to_summary(),
    )
    return ctx


def stage_generate_documents(ctx: PipelineContext) -> PipelineContext:
    if ctx.semantic_model is None:
        ctx.errors.append("Cannot generate: no semantic model")
        return ctx

    LanguageRegistry.load_builtins()
    generator = LanguageGenerator()

    for lang_code in ctx.config.languages:
        if not LanguageRegistry.has(lang_code):
            ctx.warnings.append(f"Language '{lang_code}' not registered, skipping")
            continue
        profile = LanguageRegistry.get(lang_code)
        ctx.generated_documents[lang_code] = generator.generate(
            ctx.semantic_model,
            profile,
            ctx.config,
        )

    return ctx


def stage_cross_language_review(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.review.enable_cross_language_review:
        return ctx
    if len(ctx.generated_documents) < 2:
        return ctx

    reviewer = CrossLanguageReviewer()
    ctx.cross_language_review = reviewer.review(ctx.generated_documents)
    return ctx


def stage_grounding_verification(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.review.enable_code_grounding_verification:
        return ctx

    verifier = CodeGroundingVerifier(
        ctx.evidence_registry,
        strict=ctx.config.strict_grounding,
    )
    ctx.grounding_report = verifier.verify(ctx.generated_documents)
    return ctx


def stage_codebase_verification(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.review.enable_codebase_verification:
        return ctx

    verifier = CodebaseVerifier(ctx.config.target_dir)
    ctx.codebase_verification_report = verifier.verify(ctx.generated_documents)
    return ctx


def count_issues(
    cross_report: CrossLanguageReview | None,
    grounding_report: GroundingReport | None,
    codebase_report: CodebaseVerificationReport | None,
) -> int:
    """Sum actionable verification issues across review reports."""
    issues = 0
    if cross_report is not None:
        issues += len(cross_report.critical_issues)
    if grounding_report is not None:
        issues += len(grounding_report.violations)
    if codebase_report is not None:
        issues += codebase_report.failed_count
    return issues


def quality_passed(
    cross_report: CrossLanguageReview | None,
    grounding_report: GroundingReport | None,
    codebase_report: CodebaseVerificationReport | None,
    config: MakeWikiConfig,
) -> bool:
    """Check whether documents satisfy all quality and grounding criteria."""
    if cross_report is not None and not cross_report.passed:
        return False
    if grounding_report is not None:
        if grounding_report.grounding_score < config.revision.min_grounding_score:
            return False
        if len(grounding_report.violations) > 0:
            return False
    if codebase_report is not None and not codebase_report.passed:
        return False
    return True


def stage_revision(ctx: PipelineContext) -> PipelineContext:
    """Iteratively verify and revise documents to resolve grounding and consistency issues."""
    if not ctx.config.revision.enabled:
        ctx.final_documents = dict(ctx.generated_documents)
        return ctx

    current_docs = ctx.generated_documents

    engine = RevisionEngine(
        auto_hedge=ctx.config.revision.auto_hedge_ungrounded,
        auto_harmonize=ctx.config.revision.auto_harmonize_code_blocks,
    )

    for round_no in range(1, ctx.config.revision.max_rounds + 1):
        # 1. Re-inspect current documents
        cross_report = None
        if ctx.config.review.enable_cross_language_review and len(current_docs) >= 2:
            cross_report = CrossLanguageReviewer().review(current_docs)

        grounding_report = None
        if ctx.config.review.enable_code_grounding_verification:
            grounding_report = CodeGroundingVerifier(
                ctx.evidence_registry,
                strict=ctx.config.strict_grounding,
            ).verify(current_docs)

        codebase_report = None
        if ctx.config.review.enable_codebase_verification:
            codebase_report = CodebaseVerifier(
                ctx.config.target_dir
            ).verify(current_docs)

        # 2. Check if already passed
        if quality_passed(
            cross_report,
            grounding_report,
            codebase_report,
            ctx.config,
        ):
            break

        issues_before = count_issues(cross_report, grounding_report, codebase_report)

        # 3. Apply revisions
        revised_docs, revision_report = engine.revise(
            current_docs,
            grounding_report=grounding_report,
            codebase_report=codebase_report,
            cross_language_report=cross_report,
        )

        revision_report.round_number = round_no
        revision_report.issues_before = issues_before
        revision_report.attempted_fixes = revision_report.total_actions

        # 4. If no actions were performed, stop
        if revision_report.total_actions == 0:
            revision_report.issues_after = issues_before
            revision_report.verified_resolutions = 0
            ctx.revision_reports.append(revision_report)
            if ctx.config.revision.stop_on_no_progress:
                break
            continue

        # 5. Re-verify to calculate issues_after and verified_resolutions
        post_cross_report = None
        if ctx.config.review.enable_cross_language_review and len(revised_docs) >= 2:
            post_cross_report = CrossLanguageReviewer().review(revised_docs)

        post_grounding_report = None
        if ctx.config.review.enable_code_grounding_verification:
            post_grounding_report = CodeGroundingVerifier(
                ctx.evidence_registry,
                strict=ctx.config.strict_grounding,
            ).verify(revised_docs)

        post_codebase_report = None
        if ctx.config.review.enable_codebase_verification:
            post_codebase_report = CodebaseVerifier(
                ctx.config.target_dir
            ).verify(revised_docs)

        issues_after = count_issues(
            post_cross_report, post_grounding_report, post_codebase_report
        )
        revision_report.issues_after = issues_after
        revision_report.verified_resolutions = max(issues_before - issues_after, 0)
        revision_report.introduced_regressions = (
            issues_after - issues_before if issues_after > issues_before else 0
        )

        ctx.revision_reports.append(revision_report)
        current_docs = revised_docs

        if post_cross_report is not None:
            ctx.cross_language_review = post_cross_report
        if post_grounding_report is not None:
            ctx.grounding_report = post_grounding_report
        if post_codebase_report is not None:
            ctx.codebase_verification_report = post_codebase_report

        if quality_passed(
            post_cross_report,
            post_grounding_report,
            post_codebase_report,
            ctx.config,
        ):
            break

    ctx.final_documents = current_docs
    ctx.revision_rounds = len(ctx.revision_reports)
    ctx.revision_report = ctx.revision_reports[-1] if ctx.revision_reports else None
    return ctx


def stage_write_output(ctx: PipelineContext) -> PipelineContext:
    """Write revised documents and metadata index to disk."""
    output_dir = ctx.config.target_dir / ctx.config.output_dir
    manager = OutputManager(
        output_dir,
        overwrite=ctx.config.overwrite,
        delete_stale_files=ctx.config.delete_stale_files,
    )
    written = manager.write_documents(ctx.final_documents)
    manager.write_index(ctx.final_documents, ctx.config.default_language)
    ctx.written_files = [str(path) for path in written]

    validator = OutputValidator(ctx.config.documentation_policy)
    ctx.validation_report = validator.validate(output_dir)
    return ctx


def stage_compile_site(ctx: PipelineContext) -> PipelineContext:
    if not ctx.config.site.compile:
        return ctx
    output_dir = ctx.config.target_dir / ctx.config.output_dir
    if not output_dir.is_dir():
        return ctx

    from makewiki_skills.renderer.site_compiler import SiteCompiler

    compiler = SiteCompiler(
        theme=ctx.config.site.theme,
        title=f"{ctx.config.target_dir.name} Documentation",
        include_search=ctx.config.site.include_search,
    )
    site_output = output_dir / ctx.config.site.output_subdir
    written = compiler.compile(output_dir, site_output)
    ctx.written_files.extend(written)
    return ctx


STAGES = [
    ("detect_project", stage_detect_project),
    ("collect_evidence", stage_collect_evidence),
    ("build_claims", stage_build_claims),
    ("verify_claims", stage_verify_claims),
    ("build_semantic_model", stage_build_semantic_model),
    ("generate_documents", stage_generate_documents),
    ("cross_language_review", stage_cross_language_review),
    ("grounding_verification", stage_grounding_verification),
    ("codebase_verification", stage_codebase_verification),
    ("revision", stage_revision),
    ("write_output", stage_write_output),
    ("compile_site", stage_compile_site),
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


def _build_identity(
    registry: EvidenceRegistry,
    detection: ProjectDetectionResult,
) -> ProjectIdentity:
    identity = ProjectIdentity(name=detection.project_name)

    versions = registry.query(fact_type="version")
    if versions:
        identity.version = versions[0].value
        identity.evidence.extend(versions[0].evidence)

    descs = registry.query(fact_type="description")
    if descs:
        identity.description = descs[0].value
        identity.evidence.extend(descs[0].evidence)

    return identity


def _build_installation(
    registry: EvidenceRegistry,
    detection: ProjectDetectionResult,
) -> InstallationGuide:
    """Build an installation guide from mechanically-proven install commands.

    Only install commands actually found in the repository's "install/setup"
    sections are included. When no install command is proven, the guide is
    empty (UNKNOWN) — Python never injects a guessed default like
    ``pip install -e .`` or a canned "Clone the repository" step.
    """
    prereqs = _build_prerequisites(registry, detection)
    install_facts = _commands_from_sections(registry, _INSTALL_SECTION_KEYWORDS)
    install_commands: list[str] = []
    install_evidence: list[EvidenceLink] = []
    for fact in install_facts:
        value = fact.value or ""
        if value and not _is_repo_navigation_command(value):
            install_commands.append(value)
        install_evidence.extend(fact.evidence)

    # Only build steps from proven commands. No fabricated default, no canned
    # git-clone preamble.
    steps = []
    for order, command in enumerate(
        dict.fromkeys(install_commands),  # dedupe, preserve order
        start=1,
    ):
        steps.append(
            InstallStep(
                order=order,
                title=_installation_step_title(command),
                commands=[command],
                evidence=[
                    link
                    for fact in install_facts
                    if (fact.value or "") == command
                    for link in fact.evidence
                ],
            )
        )

    installation_evidence = [link for prereq in prereqs for link in prereq.evidence]
    installation_evidence.extend(install_evidence)

    return InstallationGuide(
        prerequisites=prereqs,
        steps=steps,
        verify_command=_verify_command(registry),
        evidence=installation_evidence,
    )


def _build_prerequisites(
    registry: EvidenceRegistry,
    detection: ProjectDetectionResult,
) -> list[Prerequisite]:
    """Mechanically-derived prerequisites (runtime + version constraint).

    A prerequisite name/version is only reported when the repository declares
    it (``requires-python``, ``engines.node``). No runtime is assumed.
    """
    if detection.project_type in (
        ProjectType.PYTHON_CLI,
        ProjectType.PYTHON_LIBRARY,
        ProjectType.PYTHON_SERVICE,
    ):
        fact = _find_config_fact(registry, "project.requires-python")
        if fact is None:
            return []
        return [
            Prerequisite(
                name="Python",
                version_constraint=_extract_config_value(fact) if fact else None,
                evidence=fact.evidence if fact else [],
            )
        ]

    if detection.project_type in (
        ProjectType.NODE_CLI,
        ProjectType.NODE_REACT,
        ProjectType.NODE_LIBRARY,
    ):
        fact = _find_first_config_fact(registry, ["engines.node", "package.engines.node"])
        if fact is None:
            return []
        return [
            Prerequisite(
                name="Node.js",
                version_constraint=_extract_config_value(fact) if fact else None,
                evidence=fact.evidence if fact else [],
            )
        ]

    # Rust / Go runtimes are NOT assumed absent evidence. Return UNKNOWN (empty).
    return []


def _build_configuration(registry: EvidenceRegistry) -> list[ConfigSection]:
    cfg_facts = registry.query(fact_type="config_key")
    if not cfg_facts:
        return []

    by_source: dict[str, list[EvidenceFact]] = {}
    for fact in cfg_facts:
        source = _primary_source(fact) or "unknown"
        if not _is_user_facing_config(source):
            continue
        by_source.setdefault(source, []).append(fact)

    sections: list[ConfigSection] = []
    for source, facts in sorted(by_source.items()):
        leaf_facts = _leaf_config_facts(facts)
        if not leaf_facts:
            continue

        sections.append(
            ConfigSection(
                name=_configuration_section_name(source),
                config_file=source,
                items=[
                    ConfigItem(
                        key=fact.value or fact.claim,
                        default_value=_extract_config_value(fact),
                        source_file=source,
                        evidence=fact.evidence,
                    )
                    for fact in leaf_facts
                ],
                evidence=[link for fact in leaf_facts for link in fact.evidence],
            )
        )

    return sections


def _build_commands(registry: EvidenceRegistry) -> list[Command]:
    commands: list[Command] = []
    seen: set[str] = set()

    for fact in registry.query(fact_type="command"):
        name = fact.value or fact.claim
        if name in seen:
            continue
        seen.add(name)
        commands.append(
            Command(
                name=name,
                synopsis=name,
                description=_command_description(fact),
                section=_primary_section(fact),
                source_file=_primary_source(fact),
                evidence=fact.evidence,
            )
        )

    return commands


def _commands_from_sections(
    registry: EvidenceRegistry,
    keywords: tuple[str, ...],
) -> list[EvidenceFact]:
    return [
        fact
        for fact in registry.query(fact_type="command")
        if _section_matches(_primary_section(fact), keywords)
    ]


def _section_matches(section: str | None, keywords: tuple[str, ...]) -> bool:
    if not section:
        return False
    normalized = section.lower()
    return any(keyword in normalized for keyword in keywords)


def _primary_section(fact: EvidenceFact) -> str | None:
    return next((link.section for link in fact.evidence if link.section), None)


def _primary_source(fact: EvidenceFact) -> str | None:
    return fact.evidence[0].source_path if fact.evidence else None


def _find_config_fact(registry: EvidenceRegistry, key: str) -> EvidenceFact | None:
    return next(
        (fact for fact in registry.query(fact_type="config_key") if fact.value == key),
        None,
    )


def _find_first_config_fact(
    registry: EvidenceRegistry,
    keys: list[str],
) -> EvidenceFact | None:
    for key in keys:
        fact = _find_config_fact(registry, key)
        if fact is not None:
            return fact
    return None


def _extract_config_value(fact: EvidenceFact | None) -> str | None:
    if fact is None or not fact.evidence:
        return None
    match = re.search(r"=\s*(.+)$", fact.evidence[0].raw_text)
    if not match:
        return None
    value = match.group(1).strip().strip("\"'")
    if value in {"{}", "[]"}:
        return None
    return value


def _leaf_config_facts(facts: list[EvidenceFact]) -> list[EvidenceFact]:
    keys = [fact.value or fact.claim for fact in facts]
    return [
        fact
        for fact in facts
        if not any(
            other != (fact.value or fact.claim)
            and other.startswith(f"{(fact.value or fact.claim)}.")
            for other in keys
        )
    ]


def _command_description(fact: EvidenceFact) -> str | None:
    name = fact.value or fact.claim
    claim = fact.claim.strip()
    if claim == f"Available command: {name}":
        return None
    if claim.startswith("Command from ") or claim.startswith("Command:"):
        return None
    if claim.startswith("CLI entrypoint:"):
        return "CLI entrypoint exposed by the project."
    return claim


def _is_user_facing_config(source: str) -> bool:
    name = Path(source).name.lower()
    if name in _MANIFEST_CONFIG_FILES:
        return False
    if name.startswith(".env") or name.endswith(".env") or name.endswith(".md") or "doc" in name:
        return True
    return any(token in name for token in ("config", "settings", "appsettings"))


def _configuration_section_name(source: str) -> str:
    name = Path(source).name.lower()
    if name.startswith(".env") or name.endswith(".env") or name.endswith(".md") or "doc" in name:
        return "Environment variables"
    return "Configuration file"


def _is_repo_navigation_command(command: str) -> bool:
    normalized = command.strip().lower()
    return normalized.startswith("git clone ") or normalized.startswith("cd ")


def _installation_step_title(command: str) -> str:
    normalized = command.lower()
    if normalized.startswith(
        ("pip install", "npm install", "pnpm install", "yarn install", "poetry install")
    ):
        return "Install the project"
    if normalized.startswith("uv sync"):
        return "Sync the project environment"
    if normalized.startswith(("cargo build", "go build")):
        return "Build the project"
    return "Run the documented setup command"


def _verify_command(registry: EvidenceRegistry) -> str | None:
    for fact in _commands_from_sections(registry, _USAGE_SECTION_KEYWORDS):
        value = (fact.value or "").strip()
        if value and not value.startswith("make "):
            return value
    return None


_INSTALL_SECTION_KEYWORDS = (
    "getting started",
    "install",
    "installation",
    "quick start",
    "setup",
)

_USAGE_SECTION_KEYWORDS = (
    "example",
    "examples",
    "quick start",
    "usage",
    "use",
)

_MANIFEST_CONFIG_FILES = {
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pyproject.toml",
    "uv.lock",
    "yarn.lock",
}
