"""Pipeline orchestrator - the 7-stage document generation pipeline."""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import GeneratedDocument, LanguageGenerator
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.semantic_model import (
    Command,
    CommandGroup,
    ConfigItem,
    ConfigSection,
    FAQItem,
    InstallationGuide,
    InstallStep,
    PlatformNote,
    Prerequisite,
    ProjectIdentity,
    SemanticModel,
    TroubleshootingItem,
    UserTask,
    UsageExample,
)
from makewiki_skills.model.task_inference import TaskInferenceEngine
from makewiki_skills.renderer.output_manager import OutputManager
from makewiki_skills.renderer.validator import OutputValidator, ValidationReport
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReview, CrossLanguageReviewer
from makewiki_skills.scanner.evidence_collector import CollectedEvidence, EvidenceCollector
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectDetector, ProjectType
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink
from makewiki_skills.verification.code_grounding_verifier import CodeGroundingVerifier, GroundingReport


class PipelineContext(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: MakeWikiConfig

    detection: ProjectDetectionResult | None = None
    collected_evidence: CollectedEvidence | None = None
    evidence_registry: EvidenceRegistry = Field(default_factory=EvidenceRegistry)
    semantic_model: SemanticModel | None = None
    generated_documents: dict[str, list[GeneratedDocument]] = Field(default_factory=dict)
    cross_language_review: CrossLanguageReview | None = None
    grounding_report: GroundingReport | None = None
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


def stage_build_semantic_model(ctx: PipelineContext) -> PipelineContext:
    if ctx.detection is None or ctx.collected_evidence is None:
        ctx.errors.append("Cannot build model: missing detection or evidence")
        return ctx

    registry = ctx.evidence_registry
    identity = _build_identity(registry, ctx.detection)
    installation = _build_installation(registry, ctx.detection)
    configuration = _build_configuration(registry)
    commands = _build_commands(registry)

    engine = TaskInferenceEngine()
    user_tasks = engine.infer(commands, configuration, ctx.detection, registry)
    usage_examples = _build_usage_examples(commands, user_tasks)
    platform_notes = _build_platform_notes(commands)
    faq = _build_faq(installation, configuration, platform_notes)
    troubleshooting = _build_troubleshooting(installation, platform_notes)

    depth = ctx.config.content_depth
    is_detailed = _is_detailed_mode(depth.mode, commands, configuration, user_tasks)

    max_faq = depth.max_faq_items if is_detailed else min(depth.max_faq_items, 4)
    max_examples = depth.max_usage_examples if is_detailed else min(depth.max_usage_examples, 4)
    max_trouble = depth.max_troubleshooting_items if is_detailed else min(depth.max_troubleshooting_items, 3)

    faq = faq[:max_faq]
    usage_examples = usage_examples[:max_examples]
    troubleshooting = troubleshooting[:max_trouble]

    command_groups = _build_command_groups(
        commands, user_tasks, usage_examples, depth.split_usage_threshold, is_detailed,
        configuration=configuration,
    )

    ctx.semantic_model = SemanticModel(
        model_id=uuid.uuid4().hex[:12],
        identity=identity,
        installation=installation,
        configuration=configuration,
        commands=commands,
        user_tasks=user_tasks,
        usage_examples=usage_examples,
        faq=faq,
        platform_notes=platform_notes,
        troubleshooting=troubleshooting,
        command_groups=command_groups,
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

    verifier = CodeGroundingVerifier(ctx.evidence_registry)
    ctx.grounding_report = verifier.verify(ctx.generated_documents)
    return ctx


def stage_revision_and_output(ctx: PipelineContext) -> PipelineContext:
    ctx.final_documents = dict(ctx.generated_documents)

    output_dir = ctx.config.target_dir / ctx.config.output_dir
    manager = OutputManager(output_dir, overwrite=ctx.config.overwrite)
    written = manager.write_documents(ctx.final_documents)
    manager.write_index(ctx.final_documents, ctx.config.default_language)
    ctx.written_files = [str(path) for path in written]

    validator = OutputValidator(ctx.config.documentation_policy)
    ctx.validation_report = validator.validate(output_dir)
    return ctx


STAGES = [
    ("detect_project", stage_detect_project),
    ("collect_evidence", stage_collect_evidence),
    ("build_semantic_model", stage_build_semantic_model),
    ("generate_documents", stage_generate_documents),
    ("cross_language_review", stage_cross_language_review),
    ("grounding_verification", stage_grounding_verification),
    ("revision_and_output", stage_revision_and_output),
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
    prereqs = _build_prerequisites(registry, detection)
    install_facts = _commands_from_sections(registry, _INSTALL_SECTION_KEYWORDS)
    install_commands = [
        fact.value or ""
        for fact in install_facts
        if fact.value and not _is_repo_navigation_command(fact.value)
    ]

    if not install_commands:
        default_install = _DEFAULT_INSTALL_COMMANDS.get(detection.project_type)
        if default_install:
            install_commands = [default_install]

    steps = [
        InstallStep(
            order=1,
            title="Clone the repository",
            commands=["git clone <repository-url>", f"cd {detection.project_name}"],
        )
    ]
    if install_commands:
        steps.append(
            InstallStep(
                order=2,
                title=_installation_step_title(install_commands[0]),
                commands=install_commands[:2],
                evidence=install_facts[0].evidence if install_facts else [],
            )
        )

    installation_evidence = [link for prereq in prereqs for link in prereq.evidence]
    if install_facts:
        installation_evidence.extend(install_facts[0].evidence)

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
    if detection.project_type in (
        ProjectType.PYTHON_CLI,
        ProjectType.PYTHON_LIBRARY,
        ProjectType.PYTHON_SERVICE,
    ):
        fact = _find_config_fact(registry, "project.requires-python")
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
        return [
            Prerequisite(
                name="Node.js",
                version_constraint=_extract_config_value(fact) if fact else None,
                evidence=fact.evidence if fact else [],
            )
        ]

    if detection.project_type == ProjectType.RUST_CLI:
        return [Prerequisite(name="Rust")]

    if detection.project_type == ProjectType.GO_CLI:
        return [Prerequisite(name="Go")]

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


def _build_usage_examples(
    commands: list[Command],
    user_tasks: list[UserTask],
) -> list[UsageExample]:
    used_commands = {command for task in user_tasks for command in task.commands}
    examples: list[UsageExample] = []
    seen_commands: set[str] = set()

    for command in commands:
        if not _is_user_visible_example(command):
            continue
        if command.name in seen_commands or command.name in used_commands:
            continue

        seen_commands.add(command.name)
        examples.append(
            UsageExample(
                title=_usage_example_title(command),
                description=command.description,
                commands=[command.name],
                evidence=command.evidence,
            )
        )

    if examples:
        return examples

    for task in user_tasks[:2]:
        if not task.commands:
            continue
        examples.append(
            UsageExample(
                title=task.title,
                description=task.user_goal,
                commands=task.commands,
                evidence=task.evidence,
            )
        )

    return examples


def _build_faq(
    installation: InstallationGuide,
    configuration: list[ConfigSection],
    platform_notes: list[PlatformNote],
) -> list[FAQItem]:
    items: list[FAQItem] = []

    if installation.prerequisites:
        prereq = installation.prerequisites[0]
        version = f" {prereq.version_constraint}" if prereq.version_constraint else ""
        items.append(
            FAQItem(
                question=f"Which {prereq.name} version do I need?",
                answer=f"Project evidence points to {prereq.name}{version}.",
                evidence=prereq.evidence,
            )
        )

    if installation.verify_command:
        items.append(
            FAQItem(
                question="How do I check that the installation worked?",
                answer=f"Run `{installation.verify_command}`.",
                evidence=installation.evidence,
            )
        )

    if configuration and configuration[0].config_file:
        section = configuration[0]
        items.append(
            FAQItem(
                question="Where do I change user-facing settings?",
                answer=(
                    f"The repository exposes configuration in `{section.config_file}`. "
                    "Review that file before your first run."
                ),
                evidence=section.evidence,
            )
        )

    if platform_notes:
        items.append(
            FAQItem(
                question="Are there platform-specific steps?",
                answer=platform_notes[0].note,
                evidence=platform_notes[0].evidence,
            )
        )

    return items


def _build_platform_notes(commands: list[Command]) -> list[PlatformNote]:
    windows_notes: list[str] = []
    windows_evidence: list[EvidenceLink] = []
    make_command = next((cmd for cmd in commands if cmd.name.startswith("make ")), None)
    if make_command is not None:
        windows_notes.append(
            "The repository includes `make` targets. If `make` is unavailable on your system, "
            "run the underlying project commands directly."
        )
        windows_evidence.extend(make_command.evidence)

    unix_shell_command = next(
        (
            cmd
            for cmd in commands
            if any("rm -rf" in link.raw_text.lower() for link in cmd.evidence)
        ),
        None,
    )
    if unix_shell_command is not None:
        windows_notes.append(
            "Some helper commands use Unix shell syntax such as `rm -rf`. "
            "Run them in WSL or another Unix-like shell, or replace them with a Windows equivalent."
        )
        windows_evidence.extend(unix_shell_command.evidence)

    notes: list[PlatformNote] = []
    if windows_notes:
        notes.append(
            PlatformNote(
                platform="Windows",
                note=" ".join(windows_notes),
                evidence=windows_evidence,
            )
        )

    return _dedupe_platform_notes(notes)


def _build_troubleshooting(
    installation: InstallationGuide,
    platform_notes: list[PlatformNote],
) -> list[TroubleshootingItem]:
    items: list[TroubleshootingItem] = []
    install_command = _first_install_command(installation)

    if install_command and installation.verify_command:
        executable = installation.verify_command.split()[0]
        items.append(
            TroubleshootingItem(
                symptom=f"`{executable}` is not available after installation",
                probable_cause=(
                    "The package may not be installed in the environment you are currently using."
                ),
                solution=(
                    "Run the installation command again in the same environment, "
                    "then retry the verification command."
                ),
                commands=[install_command, installation.verify_command],
                evidence=installation.evidence,
            )
        )

    if any("`make` targets" in note.note for note in platform_notes):
        evidence = next(
            (note.evidence for note in platform_notes if "`make` targets" in note.note),
            [],
        )
        items.append(
            TroubleshootingItem(
                symptom="`make` is not recognized on your system",
                probable_cause="The repository exposes helper workflows through `make`.",
                solution="Install `make`, or run the underlying project commands directly.",
                evidence=evidence,
            )
        )

    if any("Unix shell syntax" in note.note for note in platform_notes):
        evidence = next(
            (note.evidence for note in platform_notes if "Unix shell syntax" in note.note),
            [],
        )
        items.append(
            TroubleshootingItem(
                symptom="A helper command fails on Windows",
                probable_cause="The repository includes Unix shell syntax such as `rm -rf`.",
                solution=(
                    "Run the command in WSL or another Unix-like shell, "
                    "or replace it with a Windows equivalent."
                ),
                evidence=evidence,
            )
        )

    return items


def _is_detailed_mode(
    mode: str,
    commands: list[Command],
    configuration: list[ConfigSection],
    user_tasks: list[UserTask],
) -> bool:
    """Decide whether to use detailed content depth.

    In "auto" mode, activate detailed using a multi-dimensional heuristic:
    if at least two of the three dimensions (commands, config items, tasks)
    exceed their individual thresholds, or the combined total is large enough.
    """
    if mode == "detailed":
        return True
    if mode == "compact":
        return False
    # auto: multi-dimensional heuristic
    cmd_count = len(commands)
    cfg_count = sum(len(s.items) for s in configuration)
    task_count = len(user_tasks)
    exceeded = sum([cmd_count >= 5, cfg_count >= 10, task_count >= 8])
    return exceeded >= 2 or (cmd_count + cfg_count + task_count) >= 15


def _build_command_groups(
    commands: list[Command],
    user_tasks: list[UserTask],
    usage_examples: list[UsageExample],
    split_threshold: int,
    is_detailed: bool,
    configuration: list[ConfigSection] | None = None,
) -> list[CommandGroup]:
    """Group commands by source file into logical modules.

    Only produces groups when there are enough commands to warrant splitting,
    the content depth allows it, AND commands originate from multiple distinct
    source files. A single README with many sections is not enough to split —
    the project needs genuinely separate documentation sources (e.g. README
    + Makefile + separate docs files).

    Each group is enriched with related config sections (matched via
    task.related_config) and a generated description summarising the
    user tasks it covers.

    Returns an empty list when the project is simple enough for a single
    basic-usage page.
    """
    if not is_detailed or len(commands) < split_threshold:
        return []

    # Group by source file (not section) to avoid splitting one README
    # into multiple "modules"
    by_source: dict[str, list[Command]] = {}
    ungrouped: list[Command] = []

    for cmd in commands:
        source = cmd.source_file
        if source:
            by_source.setdefault(source, []).append(cmd)
        else:
            ungrouped.append(cmd)

    # Need at least 2 distinct source files to justify splitting
    if len(by_source) < 2:
        return []

    # Build config lookup: config item key -> ConfigSection
    config_by_key: dict[str, ConfigSection] = {}
    if configuration:
        for section in configuration:
            for item in section.items:
                config_by_key[item.key] = section

    groups: list[CommandGroup] = []
    task_by_cmd: dict[str, UserTask] = {}
    for task in user_tasks:
        for cmd_name in task.commands:
            task_by_cmd[cmd_name] = task

    example_by_cmd: dict[str, UsageExample] = {}
    for ex in usage_examples:
        for cmd_name in ex.commands:
            example_by_cmd[cmd_name] = ex

    for source_name, cmds in sorted(by_source.items()):
        display_name = Path(source_name).stem.replace("_", " ").replace("-", " ").title()
        slug = re.sub(r"[^a-z0-9]+", "-", Path(source_name).stem.lower()).strip("-") or "general"
        group_tasks = [task_by_cmd[c.name] for c in cmds if c.name in task_by_cmd]
        group_examples = [example_by_cmd[c.name] for c in cmds if c.name in example_by_cmd]

        # Collect config sections related to this group's tasks
        group_configs = _collect_group_configs(group_tasks, config_by_key)

        # Generate a description from the group's tasks
        description = _generate_group_description(group_tasks)

        groups.append(
            CommandGroup(
                name=display_name,
                slug=slug,
                description=description,
                commands=cmds,
                user_tasks=group_tasks,
                usage_examples=group_examples,
                config_sections=group_configs,
                evidence=[link for c in cmds for link in c.evidence],
            )
        )

    if ungrouped:
        group_tasks = [task_by_cmd[c.name] for c in ungrouped if c.name in task_by_cmd]
        group_examples = [example_by_cmd[c.name] for c in ungrouped if c.name in example_by_cmd]
        group_configs = _collect_group_configs(group_tasks, config_by_key)
        description = _generate_group_description(group_tasks)
        groups.append(
            CommandGroup(
                name="General",
                slug="general",
                description=description,
                commands=ungrouped,
                user_tasks=group_tasks,
                usage_examples=group_examples,
                config_sections=group_configs,
                evidence=[link for c in ungrouped for link in c.evidence],
            )
        )

    return groups


def _collect_group_configs(
    group_tasks: list[UserTask],
    config_by_key: dict[str, ConfigSection],
) -> list[ConfigSection]:
    """Collect unique ConfigSections referenced by a group's tasks."""
    related_keys: set[str] = set()
    for task in group_tasks:
        related_keys.update(task.related_config)
    # Deduplicate by section identity (use id to handle duplicate references)
    seen: dict[int, ConfigSection] = {}
    for key in related_keys:
        section = config_by_key.get(key)
        if section is not None and id(section) not in seen:
            seen[id(section)] = section
    return list(seen.values())


def _generate_group_description(
    group_tasks: list[UserTask],
) -> str | None:
    """Generate a brief description for a command group based on its tasks."""
    if not group_tasks:
        return None
    goals = [t.user_goal for t in group_tasks if t.user_goal]
    if not goals:
        return None
    if len(goals) == 1:
        return goals[0]
    return f"{goals[0]} This section also covers: {goals[1]}."


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
    if name.startswith(".env"):
        return True
    return any(token in name for token in ("config", "settings", "appsettings"))


def _configuration_section_name(source: str) -> str:
    return "Environment variables" if Path(source).name.lower().startswith(".env") else "Configuration file"


def _is_repo_navigation_command(command: str) -> bool:
    normalized = command.strip().lower()
    return normalized.startswith("git clone ") or normalized.startswith("cd ")


def _installation_step_title(command: str) -> str:
    normalized = command.lower()
    if normalized.startswith(("pip install", "npm install", "pnpm install", "yarn install", "poetry install")):
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


def _is_user_visible_example(command: Command) -> bool:
    if _section_matches(command.section, _USAGE_SECTION_KEYWORDS):
        return True

    normalized = command.name.lower()
    if normalized.startswith(("docker compose", "docker-compose")):
        return True

    parts = normalized.split()
    if len(parts) < 2:
        return False
    if parts[0] in {"make", "npm", "pip", "pnpm", "python", "pytest", "ruff", "uv", "yarn"}:
        return False
    if any(token in normalized for token in (" test", " lint", " clean", " build")):
        return False
    return True


def _usage_example_title(command: Command) -> str:
    if re.search(r"(?:^|\s)(?:serve|start|run|dev)(?:\s|$)", command.name.lower()):
        return "Start the application"

    parts = command.name.split()
    if len(parts) >= 2 and not parts[1].startswith("-"):
        return f"Run the `{parts[1]}` command"
    return "Run the documented command"


def _dedupe_platform_notes(notes: list[PlatformNote]) -> list[PlatformNote]:
    deduped: list[PlatformNote] = []
    seen: set[tuple[str, str]] = set()
    for note in notes:
        key = (note.platform, note.note)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(note)
    return deduped


def _first_install_command(installation: InstallationGuide) -> str | None:
    for step in installation.steps:
        for command in step.commands:
            if not _is_repo_navigation_command(command):
                return command
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

_DEFAULT_INSTALL_COMMANDS: dict[ProjectType, str] = {
    ProjectType.PYTHON_CLI: "pip install -e .",
    ProjectType.PYTHON_LIBRARY: "pip install -e .",
    ProjectType.PYTHON_SERVICE: "pip install -e .",
    ProjectType.NODE_CLI: "npm install",
    ProjectType.NODE_REACT: "npm install",
    ProjectType.NODE_LIBRARY: "npm install",
    ProjectType.RUST_CLI: "cargo build --release",
    ProjectType.GO_CLI: "go build .",
}
