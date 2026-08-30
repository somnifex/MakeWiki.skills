"""Orchestrate the documentation pipeline.

**LEGACY deterministic scaffold — NOT the authoritative writer.**

The authoritative MakeWiki writer is the LLM Language Writer subagent driven by
the ``/makewiki`` skill flow. This ``Pipeline`` is the deprecated mechanical
scaffold kept for regression/testing only: it drives the deterministic
``LegacyDeterministicRenderer`` (Jinja) through the verify -> revise -> write
loop. It never authors semantic/narrative content in Python — every narrative
slot either comes from the ``SemanticModel`` (LLM-authored fields) or is
reported as an honest UNKNOWN marker.
"""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import LegacyDeterministicRenderer
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.claim import (
    ClaimSet,
    build_claims_from_evidence,
    verify_claims_against_codebase,
)
from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.model.semantic_model import (
    Command,
    ConfigItem,
    ConfigSection,
    InstallationGuide,
    InstallStep,
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
    MechanicalRepairEngine,
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
    generated_documents: dict[str, list[DocumentArtifact]] = Field(default_factory=dict)
    cross_language_review: CrossLanguageReview | None = None
    grounding_report: GroundingReport | None = None
    codebase_verification_report: CodebaseVerificationReport | None = None
    revision_reports: list[RevisionReport] = Field(default_factory=list)
    revision_rounds: int = 0
    revision_report: RevisionReport | None = None
    final_documents: dict[str, list[DocumentArtifact]] = Field(default_factory=dict)
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
    # legacy deterministic scaffold — NOT the authoritative writer. The
    # authoritative /makewiki writer is the LLM Language Writer subagent.
    if ctx.semantic_model is None:
        ctx.errors.append("Cannot generate: no semantic model")
        return ctx

    LanguageRegistry.load_builtins()
    generator = LegacyDeterministicRenderer()

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

    engine = MechanicalRepairEngine(
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
    """LEGACY deterministic scaffold pipeline.

    NOT the authoritative writer. The authoritative MakeWiki flow is the LLM
    Language Writer subagent driven by ``/makewiki`` (see ``SKILL.md``). This
    class is the deprecated mechanical pipeline kept for regression/testing and
    mechanical fallback; it drives the ``LegacyDeterministicRenderer`` and never
    authors semantic/narrative content in Python.
    """

    _LEGACY_WRITER = True  # explicit marker: the document-generation stage is a legacy scaffold

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
    """Build configuration sections as MECHANICAL extraction.

    Every config source that yields ``config_key`` facts is recorded with its
    raw filename as a neutral label. Python does NOT decide narrative labeling
    ("user-facing" vs "manifest", "Environment variables" vs "Configuration
    file") — that is the LLM/Skill's job. The only exclusion is mechanical:
    build-metadata schema files (``pyproject.toml``, ``package.json``, …) are
    provably build/packaging metadata, not runtime user configuration, so they
    are skipped by exact filename, never by fuzzy narrative judgment. A source
    whose name cannot be attributed is dropped (UNKNOWN), never guessed.
    """
    cfg_facts = registry.query(fact_type="config_key")
    if not cfg_facts:
        return []

    by_source: dict[str, list[EvidenceFact]] = {}
    for fact in cfg_facts:
        source = _primary_source(fact) or "unknown"
        by_source.setdefault(source, []).append(fact)

    sections: list[ConfigSection] = []
    for source, facts in sorted(by_source.items()):
        if source == "unknown":
            # Cannot mechanically attribute the keys to a file; record UNKNOWN
            # (omit) rather than fabricating a source identity.
            continue
        if Path(source).name in _BUILD_METADATA_FILES:
            # Exact, mechanical build-metadata schema exclusion. Not a
            # narrative "user-facing" decision — these are provably build
            # manifests, not runtime user configuration.
            continue
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
    """Return the mechanically-extracted description only.

    Boilerplate mechanical claims ("Available command: …", "Command from …",
    "CLI entrypoint: …") carry no real description — Python returns UNKNOWN
    (``None``) rather than fabricating one. Narrative description of a command
    is the LLM/Skill's job.
    """
    name = fact.value or fact.claim
    claim = fact.claim.strip()
    if claim == f"Available command: {name}":
        return None
    if claim.startswith("Command from ") or claim.startswith("Command:"):
        return None
    if claim.startswith("CLI entrypoint:"):
        return None  # no prose description is proven -> UNKNOWN, never fabricated
    return claim


def _configuration_section_name(source: str) -> str:
    """Return a MECHANICAL, neutral label for a config source.

    The neutral label is the raw filename. Python deliberately does NOT decide
    narrative labels ("user-facing", "Environment variables", "Configuration
    file") — deciding what a config file means for users is the LLM/Skill's
    job. A name that cannot be derived from the raw path is left as-is (the
    raw filename is always provable, so this never fabricates a label).
    """
    if not source:
        return "UNKNOWN"
    return Path(source).name


def _is_repo_navigation_command(command: str) -> bool:
    normalized = command.strip().lower()
    return normalized.startswith("git clone ") or normalized.startswith("cd ")


def _installation_step_title(command: str) -> str:
    """Return a MECHANICAL, neutral title for an install step.

    The title is the proven command itself — never a fabricated narrative like
    "Install the project". Natural-language step descriptions and translations
    are the LLM Language Writer's job in the authoritative /makewiki flow. The
    command is the honest, mechanically-proven content of the step, so it is
    used verbatim as a neutral title.
    """
    return command


def _verify_command(registry: EvidenceRegistry) -> str | None:
    """Return the explicit verify command, or UNKNOWN (``None``).

    The deterministic scaffold never guesses a canonical verify command by a
    prefix heuristic, and it never silently excludes ``make ...`` commands. A
    verify command is only reported when an explicit LLM-authored one exists on
    the model; this builder has no way to receive one, so it returns UNKNOWN
    rather than fabricating or picking one.
    """
    del registry  # explicit verify commands are LLM-authored, not guessed here
    return None


_INSTALL_SECTION_KEYWORDS = (
    "getting started",
    "install",
    "installation",
    "quick start",
    "setup",
)


# Build-metadata schema files, excluded from user-facing configuration by
# EXACT mechanical filename. These are deterministically build/packaging
# manifests (per their declared schemas), not runtime user configuration. This
# is a mechanical proof, not a narrative "user-facing" judgment.
_BUILD_METADATA_FILES = frozenset(
    {
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pyproject.toml",
        "uv.lock",
        "yarn.lock",
        "Cargo.toml",
        "Cargo.lock",
        "go.mod",
        "go.sum",
    }
)
