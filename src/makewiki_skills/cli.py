import json as json_lib
import re
import sys
from pathlib import Path
from typing import Any, cast

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

import typer
from rich.console import Console
from rich.table import Table

from makewiki_skills.config import MakeWikiConfig

app = typer.Typer(
    name="makewiki",
    help="Internal toolkit CLI for MakeWiki skills.",
    add_completion=False,
)
console = Console()

#: Canonical artifact root under a MakeWiki target directory.
_ARTIFACT_DIRNAME = ".makewiki-artifacts"


def resolve_artifact_target(wiki_dir: Path) -> Path | None:
    """Locate the target directory holding the ``.makewiki-artifacts/`` tree.

    Priority: the wiki's parent (the default layout ``<target>/.makewiki-
    artifacts/`` next to ``<target>/<output_dir>/``), then the wiki directory
    itself (a target whose output dir doubles as the root). Returns ``None``
    when neither exists — the artifact context is unavailable.
    """
    if (wiki_dir.parent / _ARTIFACT_DIRNAME).is_dir():
        return wiki_dir.parent
    if (wiki_dir / _ARTIFACT_DIRNAME).is_dir():
        return wiki_dir
    return None


@app.command(name="evidence")
def evidence(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Scan a project and emit the collected evidence facts.

    Emits facts only — deterministic extractions (commands, config keys,
    paths, versions) with their source evidence. Python never interprets what
    the repository means; that is the LLM's job.
    """
    from makewiki_skills.scanner.evidence_bundle import EvidenceBundle
    from makewiki_skills.scanner.evidence_collector import EvidenceCollector
    from makewiki_skills.scanner.project_detector import ProjectDetector

    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    detector = ProjectDetector()
    detection = detector.detect(target)
    collector = EvidenceCollector(cfg)
    collected = collector.collect(target, detection)

    if output_format == "json":
        bundle = EvidenceBundle.from_registry(
            detection=detection,
            facts=collected.facts,
            files_read=collected.raw_files_read,
            claims=[],
            coverage=collected.coverage.model_dump(),
        )
        typer.echo(json_lib.dumps(bundle.model_dump(), indent=2, ensure_ascii=False))
        return

    console.print(f"[bold]Project:[/bold] {detection.project_name}")
    console.print(f"[bold]Type:[/bold] {detection.project_type.value}")
    console.print(f"[bold]Confidence:[/bold] {detection.confidence:.0%}")
    console.print(f"[bold]Indicators:[/bold] {', '.join(detection.indicators_found)}")
    console.print()

    summary: dict[str, int] = {}
    for f in collected.facts:
        summary[f.fact_type] = summary.get(f.fact_type, 0) + 1

    table = Table(title="Evidence Summary")
    table.add_column("Fact Type")
    table.add_column("Count", justify="right")
    for ftype, count in sorted(summary.items()):
        table.add_row(ftype, str(count))
    console.print(table)
    console.print(f"Total facts: {len(collected.facts)}")


@app.command(name="scan")
def scan_alias(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Deprecated alias for `evidence`. Retained for backward compatibility."""
    evidence(target, config_path, output_format)


@app.command(name="coverage")
def coverage(
    target: Path = typer.Argument(..., help="Target project directory"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Report deterministic mechanical coverage of a discovery pass.

    Pure bookkeeping: what was discovered, inspected, skipped (with reason),
    and ignored by the mechanical walk, plus which categories the walk did not
    touch (uncovered_categories) and low-confidence facts. No semantic
    judgment — the LLM Scout layer owns resolving the gaps this reports.
    """
    from makewiki_skills.scanner.evidence_collector import EvidenceCollector
    from makewiki_skills.scanner.project_detector import ProjectDetector

    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {target}")
        raise typer.Exit(1)

    cfg = _load_config(None, target)
    detector = ProjectDetector()
    detection = detector.detect(target)
    collector = EvidenceCollector(cfg)
    collected = collector.collect(target, detection)
    report = collected.coverage

    if output_format == "json":
        typer.echo(json_lib.dumps(report.model_dump(), indent=2, ensure_ascii=False))
        return

    console.print(f"[bold]Coverage:[/bold] {target}")
    console.print(f"[bold]Files discovered:[/bold] {report.files_discovered}")
    console.print(f"[bold]Files read:[/bold] {report.files_read}")
    console.print(f"[bold]Files parsed:[/bold] {report.files_parsed}")
    console.print(f"[bold]Files with facts:[/bold] {report.files_with_facts}")
    console.print(f"[bold]Inspected by tool:[/bold] {len(report.files_inspected_by_tool)}")
    console.print(
        f"[bold]Skipped:[/bold] {len(report.files_skipped)} "
        f"(skipped_due_to_max_files: {report.skipped_due_to_max_files})"
    )
    console.print(f"[bold]Ignored:[/bold] {len(report.ignored_files)}")

    if report.files_by_category:
        table = Table(title="Files by Category")
        table.add_column("Category")
        table.add_column("Count", justify="right")
        for cat, count in sorted(report.files_by_category.items()):
            table.add_row(cat, str(count))
        console.print(table)

    if report.uncovered_categories:
        console.print("[bold]Uncovered categories (LLM must scout manually):[/bold]")
        for cat in report.uncovered_categories:
            console.print(f"  - {cat}")
    else:
        console.print("[green]All mechanical categories covered by the walk.[/green]")


@app.command()
def validate(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ output directory"),
) -> None:
    """Validate an existing makewiki output directory."""
    from makewiki_skills.renderer.validator import OutputValidator

    wiki_dir = Path(wiki_dir).resolve()
    validator = OutputValidator()
    report = validator.validate(wiki_dir)

    console.print(f"[bold]{report.summary()}[/bold]")
    for issue in report.issues:
        severity_color = "red" if issue.severity == "error" else "yellow"
        console.print(
            f"  [{severity_color}]{issue.severity}[/{severity_color}] {issue.issue_type}: {issue.message}"
        )

    if report.passed:
        console.print("[green]Validation passed.[/green]")
    else:
        console.print("[red]Validation failed.[/red]")
        raise typer.Exit(1)


@app.command(name="lint-drafts")
def lint_drafts(
    wiki_dir: Path = typer.Argument(..., help="Path to assembled makewiki/ output directory"),
    structural_only: bool = typer.Option(
        False,
        "--structural-only",
        help="Run only pure-Markdown structural checks (frontmatter leaks, "
        "artifact-path leaks, section markers, duplicate block IDs) and skip "
        "every V3 cross-artifact check. Explicit opt-in for standalone scans; "
        "the default is the full Integration lint.",
    ),
) -> None:
    """Integration-time mechanical draft hygiene lint.

    Default (full Integration mode) fails closed: the canonical V3 artifacts
    (DocumentationPlan / PageSpecs / DocumentationModel) must exist and be
    schema-valid, and their cross-checks run. Blocking issues mean Integration
    is incomplete. ``--structural-only`` runs the pure-Markdown checks without
    any artifact context and clearly says the cross-artifact checks were not
    run. Never judges page quality and never changes the Quality Gate.
    """
    import yaml as yaml_lib

    from makewiki_skills.model.documentation_model import DocumentationModel
    from makewiki_skills.model.documentation_plan import DocumentationPlan
    from makewiki_skills.model.page_spec import PageSpec
    from makewiki_skills.verification.draft_lint import run_draft_lint

    wiki_dir = Path(wiki_dir).resolve()
    if not wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {wiki_dir}")
        raise typer.Exit(1)

    if structural_only:
        issues = run_draft_lint(wiki_dir, None, [], None, structural_only=True)
        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity != "error"]
        by_rule: dict[str, list] = {}
        for i in issues:
            by_rule.setdefault(i.rule, []).append(i)
        console.print(
            f"[bold]Structural draft lint[/bold] — {len(errors)} errors, "
            f"{len(warnings)} warnings"
        )
        for rule, items in sorted(by_rule.items()):
            severity = "error" if any(i.severity == "error" for i in items) else "warning"
            color = "red" if severity == "error" else "yellow"
            console.print(f"  [{color}]{rule}[/{color}]: {len(items)}")
            for i in items[:3]:
                loc = f" {i.document}:" if i.document else ""
                console.print(f"    {loc} {i.message[:120]}")
            if len(items) > 3:
                console.print(f"    ... and {len(items) - 3} more")
        if errors:
            console.print("[red]Structural draft lint found blocking errors.[/red]")
            raise typer.Exit(1)
        console.print(
            "[green]Structural draft lint passed; V3 cross-artifact checks "
            "were not run.[/green]"
        )
        return

    # Full Integration mode (fail closed): the canonical V3 artifacts must
    # exist and be schema-valid, or the lint reports incompleteness instead of
    # a false success.
    target = resolve_artifact_target(wiki_dir)
    if target is None:
        console.print(
            "[red]Error:[/red] artifact context unavailable: no "
            f"{_ARTIFACT_DIRNAME}/ found next to or inside {wiki_dir}. "
            "Run /makewiki Integration first, point at the assembled output "
            "directory of a target with artifacts, or pass --structural-only "
            "for a pure-Markdown scan."
        )
        raise typer.Exit(1)

    artifacts = target / _ARTIFACT_DIRNAME

    def _fail_closed(what: str, rule: str, detail: str) -> None:
        console.print(
            f"[red]Error:[/red] Integration lint unavailable/incomplete: "
            f"canonical V3 artifact {what} is missing or invalid — {detail}"
        )
        console.print(f"[red]Blocking rule:[/red] {rule}")
        raise typer.Exit(1)

    plan_path = artifacts / "10-documentation-plan" / "documentation_plan.yaml"
    plan: DocumentationPlan | None = None
    page_specs: list[PageSpec] = []
    doc_model: DocumentationModel | None = None
    if plan_path.is_file():
        try:
            raw = yaml_lib.safe_load(plan_path.read_text(encoding="utf-8"))
            payload = raw.get("documentation_plan") if isinstance(raw, dict) else None
            if payload is None:
                raise ValueError("missing 'documentation_plan' wrapper key")
            plan = DocumentationPlan.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 - schema drift is reported, not crashed on
            _fail_closed(
                "documentation_plan.yaml",
                "documentation_plan_invalid",
                f"schema validation failed ({str(exc)[:160]}...)",
            )
    else:
        _fail_closed(
            "documentation_plan.yaml",
            "documentation_plan_missing",
            "expected 10-documentation-plan/documentation_plan.yaml",
        )

    planned_page_count = len(set(plan.pages)) + sum(len(s.pages) for s in plan.sections)
    spec_dir = artifacts / "11-page-specs"
    spec_files = sorted(spec_dir.glob("page_specs.*.yaml")) if spec_dir.is_dir() else []
    if not spec_files:
        if planned_page_count:
            _fail_closed(
                "page_specs (11-page-specs/page_specs.*.yaml)",
                "page_specs_missing",
                "planned pages exist but no PageSpec artifact was found",
            )
    else:
        for spec_file in spec_files:
            try:
                raw = yaml_lib.safe_load(spec_file.read_text(encoding="utf-8"))
                if not (isinstance(raw, dict) and "page_specs" in raw):
                    raise ValueError("missing 'page_specs' wrapper key")
                for spec in raw["page_specs"].get("specs", []):
                    page_specs.append(PageSpec.model_validate(spec))
            except Exception as exc:  # noqa: BLE001 - report the offending file
                _fail_closed(
                    str(spec_file.relative_to(artifacts)),
                    "page_spec_invalid",
                    f"PageSpec could not be loaded ({str(exc)[:160]}...)",
                )

    model_path = artifacts / "07-documentation-model" / "documentation_model.yaml"
    if model_path.is_file():
        try:
            raw = yaml_lib.safe_load(model_path.read_text(encoding="utf-8"))
            payload = raw.get("documentation_model") if isinstance(raw, dict) else None
            if payload is None:
                raise ValueError("missing 'documentation_model' wrapper key")
            doc_model = DocumentationModel.model_validate(payload)
        except Exception as exc:  # noqa: BLE001 - schema drift is reported, not crashed on
            _fail_closed(
                "documentation_model.yaml",
                "documentation_model_invalid",
                f"schema validation failed ({str(exc)[:160]}...)",
            )
    else:
        _fail_closed(
            "documentation_model.yaml",
            "documentation_model_missing",
            "expected 07-documentation-model/documentation_model.yaml",
        )

    # Declared languages for the lint: the canonical DocumentationPlan.languages
    # (already in `plan`); when the plan is absent, fall back to the assembled
    # SitePresentationPlan (the Integration language authority). Default
    # language comes from the same plan (never assumed to be en).
    default_language = "en"
    if plan is not None and plan.languages:
        default_language = plan.languages[0]
    else:
        for candidate in ("site_presentation.yaml", "site_presentation.yml", "site_presentation.json"):
            probe = wiki_dir / candidate
            if probe.is_file():
                try:
                    site_raw = yaml_lib.safe_load(probe.read_text(encoding="utf-8"))
                    if isinstance(site_raw, dict):
                        default_language = str(site_raw.get("default_language") or "en")
                except Exception:  # noqa: BLE001 - unreadable plan: keep default
                    pass
                break

    issues = run_draft_lint(wiki_dir, plan, page_specs, doc_model, default_language=default_language)

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity != "error"]
    by_rule: dict[str, list] = {}
    for i in issues:
        by_rule.setdefault(i.rule, []).append(i)

    console.print(f"[bold]Draft lint[/bold] — {len(errors)} errors, {len(warnings)} warnings")
    for rule, items in sorted(by_rule.items()):
        severity = "error" if any(i.severity == "error" for i in items) else "warning"
        color = "red" if severity == "error" else "yellow"
        console.print(f"  [{color}]{rule}[/{color}]: {len(items)}")
        for i in items[:3]:
            loc = f" {i.document}:" if i.document else ""
            console.print(f"    {loc} {i.message[:120]}")
        if len(items) > 3:
            console.print(f"    ... and {len(items) - 3} more")

    if errors:
        console.print("[red]Integration incomplete: blocking draft-lint errors.[/red]")
        raise typer.Exit(1)
    console.print("[green]Draft lint passed.[/green]")


@app.command(name="verify-docs")
def verify_docs(
    target: Path = typer.Argument(..., help="Target project directory"),
    wiki_dir: Path | None = typer.Option(
        None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    semantic_audit: Path | None = typer.Option(
        None,
        "--semantic-audit",
        help="Path to an LLM SemanticAuditBundle JSON. When provided, L3/L4b/L5 "
        "verdicts from the bundle are merged into the report as authoritative; "
        "without it, L3/L4b/L5 are reported PENDING.",
    ),
    semantic_model: Path | None = typer.Option(
        None,
        "--semantic-model",
        help="Path to the current SemanticModel JSON. Used to prove the bundle's "
        "semantic_model_digest binding. When the bundle declares a "
        "semantic_model_digest but no --semantic-model is supplied, the model "
        "binding is UNPROVEN and L3/L4b/L5 stay PENDING.",
    ),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Run unified L0-L5 verification plus the Quality Gate on existing docs.

    Verifies that every claim in the generated documentation is grounded —
    paths exist (L1), interfaces/probes match (L2), behavior is evidenced
    (L3), languages agree (L4), and over-assertion is flagged (L5). The Quality
    Gate aggregates the layers into an honest verdict (PASS / FAIL / PENDING /
    N/A) mapped to the CI exit code via ``result.ci_exit_code``.
    """
    from makewiki_skills.languages.registry import LanguageRegistry
    from makewiki_skills.model.document_artifact import GeneratedDocument
    from makewiki_skills.verification.orchestrator import VerificationOrchestrator
    from makewiki_skills.verification.quality_gate import evaluate_quality_gate

    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs

    LanguageRegistry.load_builtins()

    resolved_wiki_dir = Path(wiki_dir).resolve() if wiki_dir else target / cfg.output_dir
    if not resolved_wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Wiki directory not found: {resolved_wiki_dir}")
        raise typer.Exit(1)

    documents: dict[str, list[GeneratedDocument]] = {}
    for lang_code in langs:
        if not LanguageRegistry.has(lang_code):
            continue
        profile = LanguageRegistry.get(lang_code)
        docs: list[GeneratedDocument] = []
        for md_file in resolved_wiki_dir.rglob("*.md"):
            if md_file.name == "index.md":
                continue
            name = md_file.name
            if lang_code == cfg.default_language:
                if any(f".{other}" in name for other in langs if other != lang_code):
                    continue
            else:
                if profile.file_suffix not in name:
                    continue

            rel = md_file.relative_to(resolved_wiki_dir)
            base_name = str(rel).replace("\\", "/")
            if profile.file_suffix:
                base_name = base_name.replace(profile.file_suffix, "")

            content = md_file.read_text(encoding="utf-8", errors="replace")
            docs.append(
                GeneratedDocument(
                    filename=str(rel).replace("\\", "/"),
                    base_name=base_name,
                    language_code=lang_code,
                    content=content,
                    word_count=len(content.split()),
                )
            )
        documents[lang_code] = docs

    orchestrator = VerificationOrchestrator(target)

    from rich.console import Console as _StderrConsole

    err = _StderrConsole(stderr=True, highlight=False)

    # Change 1: if a current SemanticModel is supplied, validate it and compute
    # its CANONICAL digest. On validation failure the audit bundle must NOT be
    # merged (L3/L4b/L5 stay pending) per the honesty policy.
    semantic_model_digest = None
    if semantic_model is not None:
        semantic_model_digest = _load_semantic_model_digest(semantic_model, err)

    if semantic_model is not None and semantic_model_digest is None:
        # Supplied but invalid -> do not merge any bundle.
        semantic_bundle = None
    else:
        semantic_bundle = _load_semantic_audit(
            semantic_audit,
            resolved_wiki_dir,
            semantic_model=semantic_model,
        )

    report = orchestrator.verify_documents(
        documents,
        wiki_dir=resolved_wiki_dir,
        semantic_bundle=semantic_bundle,
        semantic_model_digest=semantic_model_digest,
    )
    result = evaluate_quality_gate(
        report, cfg, allow_pending_llm_layers=cfg.quality.allow_pending_llm_layers
    )

    if output_format == "json":
        typer.echo(
            json_lib.dumps(
                {"report": report.model_dump(), "quality_gate": result.model_dump()},
                indent=2,
                ensure_ascii=False,
            )
        )
        raise typer.Exit(result.ci_exit_code)

    console.print("[bold]L0-L5 Verification[/bold]")
    # Mechanical layers: L0/L1/L2/L4a. Semantic/LLM layers: L3/L4b/L5.
    layer_rows = [
        ("L0", "Syntax & Structure", result.l0_status),
        ("L1", "Existence", result.l1_status),
        ("L2", "Interface", result.l2_status),
        ("L3", "Behavior (LLM)", result.l3_status),
        ("L4a", "Cross-language parity (mechanical)", result.l4a_status),
        ("L4b", "Prose parity (LLM)", result.l4b_status),
        ("L5", "Epistemic (LLM)", result.l5_status),
    ]
    for marker, label, status in layer_rows:
        console.print(f"  {marker} ({label}): {_render_layer_status(status)}")

    console.print(f"[bold]Quality Gate:[/bold] Grounding score {result.grounding_score:.1%}")
    console.print(f"  Gate verdict: {_render_gate_verdict(result)}")
    console.print(
        f"  CI exit code: {result.ci_exit_code}  "
        f"(passed=0, failed=1, pending_semantic=0/2, pending_mechanical=3)"
    )
    if result.unresolved_critical:
        console.print(f"  [yellow]Unresolved critical: {result.unresolved_critical}[/yellow]")
    if result.pending_llm_layers:
        console.print(
            f"  [yellow]Pending LLM layers: {', '.join(result.pending_llm_layers)}[/yellow]"
        )
    if result.pending_mechanical_layers:
        console.print(
            f"  [yellow]Pending mechanical layers: {', '.join(result.pending_mechanical_layers)}[/yellow]"
        )

    # Change 3: separate sections per status so pending/unknown checks are
    # NEVER labeled "Failed". `failures()` returns only status==failed.
    layers = list(report.layers.values())
    failed = [c for layer_report in layers for c in layer_report.failures()]
    pending = [c for layer_report in layers for c in layer_report.pending()]
    unknown = [c for layer_report in layers for c in layer_report.unknowns()]
    warnings = [c for layer_report in layers for c in layer_report.warnings()]

    # Aggregate repeated same-kind findings into summary rows with a few
    # examples. JSON output keeps every finding — display-only.
    if failed:
        console.print(_render_aggregated("Failed Checks (aggregated)", failed))
    if pending:
        console.print(_render_aggregated("Pending Semantic Reviews (aggregated)", pending))
    if unknown:
        console.print(_render_aggregated("Unknown / Insufficient Evidence (aggregated)", unknown))
    if warnings:
        console.print(_render_aggregated("Warnings (aggregated)", warnings))

    raise typer.Exit(result.ci_exit_code)


@app.command(name="verify")
def verify_alias(
    target: Path = typer.Argument(..., help="Target project directory"),
    wiki_dir: Path | None = typer.Option(
        None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    semantic_audit: Path | None = typer.Option(
        None,
        "--semantic-audit",
        help="Path to an LLM SemanticAuditBundle JSON. Without it, L3/L4b/L5 are PENDING.",
    ),
    semantic_model: Path | None = typer.Option(
        None,
        "--semantic-model",
        help="Path to the current SemanticModel JSON. Used to prove the bundle's "
        "semantic_model_digest binding.",
    ),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Deprecated alias for `verify-docs`.

    Retained for backward compatibility; runs the same unified L0-L5
    verification and Quality Gate.
    """
    verify_docs(target, wiki_dir, langs, config_path, semantic_audit, semantic_model, output_format)


@app.command(name="verify-claim")
def verify_claim(
    claim_file: Path = typer.Argument(..., help="Path to claim JSON (single Claim object or {'claims': [...]})"),
    target: Path = typer.Option(Path("."), "--target", "-t", help="Project directory to verify claims against"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
    project_name: str | None = typer.Option(None, "--project", "-p", help="Project name (defaults to sibling project_name)"),
) -> None:
    """Verify a Claim / ClaimSet JSON against the project filesystem.

    Loads a Claim or ClaimSet document (as produced by the Skill's Claim step
    or Python's evidence extraction), runs ``verify_claims_against_codebase``
    on it, and reports each ``MechanicalAssertion``'s per-layer verification
    status (L0-L5). This is the mechanical proof half of the Cognitive
    Authority Boundary: Python proves what it can (L0 syntax, L1 existence)
    and marks everything else pending for LLM judgment.
    """
    from makewiki_skills.model.claim import ClaimSet, verify_claims_against_codebase

    data = json_lib.loads(claim_file.read_text(encoding="utf-8"))
    project_name_val = project_name
    if isinstance(data, dict) and project_name_val is None:
        project_name_val = data.get("project_name")
    project_name_val = project_name_val or "project"

    claim_set = ClaimSet.from_llm_json(project_name_val, data)
    target = Path(target).resolve()
    verified = verify_claims_against_codebase(claim_set, target)

    if output_format == "json":
        typer.echo(json_lib.dumps(verified.model_dump(), indent=2, ensure_ascii=False))
        raise typer.Exit(0)

    console.print(f"[bold]Claim Verification[/bold]  project={verified.project_name}")
    console.print(f"  Claims: {len(verified.claims)}  target: {target}")
    table = Table(title="Per-claim L-status")
    table.add_column("Claim ID")
    table.add_column("Type")
    table.add_column("L0")
    table.add_column("L1")
    table.add_column("L2")
    table.add_column("L5")
    for claim in verified.claims:
        table.add_row(
            claim.claim_id,
            claim.claim_type,
            claim.verification.l0_syntax,
            claim.verification.l1_existence,
            claim.verification.l2_interface,
            claim.verification.l5_epistemic,
        )
    console.print(table)


@app.command(name="verify-model")
def verify_model(
    model_file: Path = typer.Argument(..., help="Path to semantic model JSON"),
    target: Path = typer.Option(Path("."), "--target", "-t", help="Project directory to cross-check evidence references against"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Validate a semantic model JSON: schema + evidence-ref existence.

    Loads a SemanticModel document, validates it against the pydantic schema,
    and mechanically proves that every evidence reference it cites actually
    exists in the target repository. Any ``evidence.source_path`` that does not
    resolve on disk is reported as a failure. This is the deterministic check
    that backs the Skill's semantic model before writers render from it.
    """
    from makewiki_skills.model.semantic_model import SemanticModel

    data = json_lib.loads(model_file.read_text(encoding="utf-8"))
    try:
        model = SemanticModel.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError
        console.print(f"[red]Schema validation failed:[/red] {exc}")
        raise typer.Exit(1)

    target = Path(target).resolve()
    missing: list[tuple[str, str]] = []
    checked = 0
    seen_refs: set[str] = set()

    def _collect_evidence(node: Any) -> None:
        nonlocal checked
        # An object (pydantic model / dict) may itself carry .evidence references.
        if isinstance(node, dict):
            src = node.get("source_path")
            if isinstance(src, str) and src:
                if src not in seen_refs:
                    seen_refs.add(src)
                    checked += 1
                    norm = src.lstrip("./")
                    is_real_path = Path(src).is_absolute() or (target / norm).exists()
                    if not is_real_path:
                        missing.append((src, ""))
                return
            ev = node.get("evidence")
            if isinstance(ev, list):
                _collect_evidence(ev)
            for value in node.values():
                _collect_evidence(value)
            return
        if isinstance(node, list):
            for item in node:
                _collect_evidence(item)
            return

        # A single EvidenceLink object.
        src = getattr(node, "source_path", None)
        if isinstance(src, str) and src:
            if src not in seen_refs:
                seen_refs.add(src)
                checked += 1
                norm = src.lstrip("./")
                is_real_path = Path(src).is_absolute() or (target / norm).exists()
                if not is_real_path:
                    missing.append((src, ""))
            return
        if hasattr(node, "evidence"):
            _collect_evidence(list(getattr(node, "evidence") or []))
            for field_name in ("prerequisites", "steps", "items", "configuration", "user_tasks", "commands"):
                child = getattr(node, field_name, None)
                if child is not None:
                    _collect_evidence(child)

    _collect_evidence(model.model_dump())

    if output_format == "json":
        typer.echo(json_lib.dumps({
            "schema_valid": True,
            "evidence_references_checked": checked,
            "evidence_references_missing": [m[0] for m in missing],
            "verified_at": getattr(model, "created_at", None),
        }, indent=2, ensure_ascii=False))
        raise typer.Exit(1 if missing else 0)

    console.print("[bold]Semantic Model Verification[/bold]")
    console.print(f"  schema: [green]valid[/green]  evidence refs checked: {checked}")
    if missing:
        console.print(f"  [red]{len(missing)} evidence reference(s) missing on disk:[/red]")
        for src, _owner in missing:
            console.print(f"    - {src}")
        raise typer.Exit(1)
    console.print("  [green]All evidence references resolve on disk.[/green]")


@app.command(name="parity")
def parity(
    target: Path = typer.Argument(..., help="Target project directory (or wiki dir)"),
    wiki_dir: Path | None = typer.Option(
        None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Compare language versions: exact block-ID parity + aligned passages.

    Runs the L4 cross-language layer to mechanically prove that structural
    elements (in particular code blocks and their stable block IDs) match across
    all requested languages, then emits aligned passages per document for the
    Skill's LLM Auditor to reason over prose parity. Mechanical exactness is
    Python's proof; semantic prose equality is the LLM's judgment.
    """
    from makewiki_skills.languages.registry import LanguageRegistry
    from makewiki_skills.model.document_artifact import GeneratedDocument
    from makewiki_skills.verification.orchestrator import VerificationOrchestrator

    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs
    LanguageRegistry.load_builtins()

    resolved_wiki_dir = Path(wiki_dir).resolve() if wiki_dir else target / cfg.output_dir
    if not resolved_wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Wiki directory not found: {resolved_wiki_dir}")
        raise typer.Exit(1)

    documents: dict[str, list[GeneratedDocument]] = {}
    for lang_code in langs:
        if not LanguageRegistry.has(lang_code):
            continue
        profile = LanguageRegistry.get(lang_code)
        docs: list[GeneratedDocument] = []
        for md_file in resolved_wiki_dir.rglob("*.md"):
            if md_file.name == "index.md":
                continue
            name = md_file.name
            if lang_code == cfg.default_language:
                if any(f".{other}" in name for other in langs if other != lang_code):
                    continue
            else:
                if profile.file_suffix not in name:
                    continue
            rel = md_file.relative_to(resolved_wiki_dir)
            base_name = str(rel).replace("\\", "/")
            if profile.file_suffix:
                base_name = base_name.replace(profile.file_suffix, "")
            content = md_file.read_text(encoding="utf-8", errors="replace")
            docs.append(
                GeneratedDocument(
                    filename=str(rel).replace("\\", "/"),
                    base_name=base_name,
                    language_code=lang_code,
                    content=content,
                )
            )
        documents[lang_code] = docs

    orchestrator = VerificationOrchestrator(target)
    l4_report = orchestrator.verify_layer("L4", documents, wiki_dir=resolved_wiki_dir)

    # Aligned passages (prose parity input for the LLM Auditor), matched by
    # STABLE SECTION ID, never by H2 text or H2 position. Sections pair
    # document-scoped: the same section id on two different pages never
    # collides because each AlignedPassage carries its document's base_name.
    from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer

    aligned: list[dict[str, Any]] = []
    for passage in CrossLanguageReviewer().align_documents(documents):
        present = [lang for lang, text in passage.texts.items() if text != "missing"]
        # Emit when there are >=2 real passages to compare, or when a language
        # that declares the document is missing this passage — the Auditor must
        # see the "missing" marker rather than have a gap papered over.
        if len(present) >= 2 or any(text == "missing" for text in passage.texts.values()):
            aligned.append({
                "review_item_id": passage.review_item_id,
                "document": passage.document_id,
                "section_id": passage.section_id,
                "block_id": passage.block_id,
                "passages": passage.texts,
            })

    if output_format == "json":
        typer.echo(json_lib.dumps({
            "l4": l4_report.model_dump(),
            "aligned_passages": aligned,
        }, indent=2, ensure_ascii=False))
        raise typer.Exit(0 if l4_report.passed else 1)

    console.print("[bold]Language Parity (L4)[/bold]")
    state = "[green]PASS[/green]" if l4_report.passed else "[red]FAIL[/red]"
    console.print(f"  L4 (Cross-language): {state}  {l4_report.passed_count}/{l4_report.total_checks}")
    for check in l4_report.failures():
        console.print(f"    [red]{check.target}[/red]: {check.detail}")
    console.print(f"[bold]Aligned passages:[/bold] {len(aligned)} item(s) ready for LLM prose review")
    raise typer.Exit(0 if l4_report.passed else 1)


@app.command()
def review(
    target: Path = typer.Argument(
        ..., help="Project directory or MakeWiki output directory (wiki_dir)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Run cross-language review on existing makewiki output."""
    from makewiki_skills.model.document_artifact import GeneratedDocument
    from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer

    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs

    from makewiki_skills.languages.registry import LanguageRegistry

    LanguageRegistry.load_builtins()

    # Accept either a project directory (whose makewiki/ output lives under
    # cfg.output_dir) OR a wiki_dir passed directly. A wiki_dir is detected by
    # the presence of README.md in the target itself.
    wiki_dir = target / cfg.output_dir
    if not wiki_dir.is_dir() and (target / "README.md").is_file():
        wiki_dir = target
    if not wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Wiki directory not found: {wiki_dir}")
        raise typer.Exit(1)

    documents: dict[str, list[GeneratedDocument]] = {}
    for lang_code in langs:
        if not LanguageRegistry.has(lang_code):
            continue
        profile = LanguageRegistry.get(lang_code)
        docs: list[GeneratedDocument] = []
        for md_file in wiki_dir.rglob("*.md"):
            if md_file.name == "index.md":
                continue
            name = md_file.name
            if lang_code == cfg.default_language:
                if any(f".{other}" in name for other in langs if other != lang_code):
                    continue
            else:
                if profile.file_suffix not in name:
                    continue
                name = name.replace(profile.file_suffix, "")

            rel = md_file.relative_to(wiki_dir)
            base_name = str(rel).replace("\\", "/")
            if profile.file_suffix:
                base_name = base_name.replace(profile.file_suffix, "")

            content = md_file.read_text(encoding="utf-8", errors="replace")
            docs.append(
                GeneratedDocument(
                    filename=str(rel).replace("\\", "/"),
                    base_name=base_name,
                    language_code=lang_code,
                    content=content,
                    word_count=len(content.split()),
                )
            )
        documents[lang_code] = docs

    reviewer = CrossLanguageReviewer()
    result = reviewer.review(documents)

    console.print("[bold]Cross-Language Review[/bold]")
    console.print(f"  Languages: {', '.join(result.languages_reviewed)}")
    console.print(f"  Consistency: {result.consistency_score:.1%}")
    console.print(f"  Issues: {len(result.fact_deltas)}")

    if result.fact_deltas:
        table = Table(title="Inconsistencies")
        table.add_column("Type")
        table.add_column("Value")
        table.add_column("Present In")
        table.add_column("Missing From")
        table.add_column("Severity")
        for delta in result.fact_deltas[:20]:
            sev_color = {"critical": "red", "major": "yellow", "minor": "dim"}.get(
                delta.severity, ""
            )
            table.add_row(
                delta.fact_type,
                delta.value[:40],
                ", ".join(delta.present_in),
                ", ".join(delta.missing_from),
                f"[{sev_color}]{delta.severity}[/{sev_color}]",
            )
        console.print(table)


@app.command(name="init-config")
def init_config(
    target: Path = typer.Argument(".", help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
) -> None:
    """Generate a default makewiki.config.yaml in the target directory."""
    target = Path(target).resolve()
    cfg = MakeWikiConfig.default(target)
    cfg.languages = langs

    config_path = target / "makewiki.config.yaml"
    config_path.write_text(cfg.to_yaml(), encoding="utf-8")
    console.print(f"[green]Created[/green] {config_path}")


@app.command(name="semantic-review")
def semantic_review(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ output directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json | human"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Prepare aligned passages for cross-language semantic review."""
    wiki_dir = Path(wiki_dir).resolve()
    if not wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {wiki_dir}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, wiki_dir)
    if not cfg.review.enable_review_pair_generation:
        console.print("[yellow]semantic-review is disabled (review.enable_review_pair_generation=false).[/yellow]")
        raise typer.Exit(0)

    from makewiki_skills.languages.registry import LanguageRegistry

    LanguageRegistry.load_builtins()

    pages: dict[str, dict[str, str]] = {}
    default_lang = langs[0] if langs else "en"

    for md_file in sorted(wiki_dir.rglob("*.md")):
        if md_file.name == "index.md":
            continue
        rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")

        detected_lang = default_lang
        base = rel
        for lang_code in langs:
            if lang_code == default_lang:
                continue
            if LanguageRegistry.has(lang_code):
                profile = LanguageRegistry.get(lang_code)
                if profile.file_suffix and profile.file_suffix in rel:
                    detected_lang = lang_code
                    base = rel.replace(profile.file_suffix, "")
                    break

        content = md_file.read_text(encoding="utf-8", errors="replace")
        pages.setdefault(base, {})[detected_lang] = content

    review_pairs: list[dict[str, Any]] = []
    expected_lang_count = max(len(langs), 1)
    fully_aligned_pages = 0
    for base_name, lang_contents in sorted(pages.items()):
        if len(lang_contents) < 2:
            continue
        if len(lang_contents) >= expected_lang_count:
            fully_aligned_pages += 1

    # Pair sections by STABLE SECTION ID per document, never by H2 text or H2
    # index, so reordered/reworded native sections still align by identity.
    from makewiki_skills.model.document_artifact import GeneratedDocument
    from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer

    l4_documents: dict[str, list[GeneratedDocument]] = {}
    for lang_code in langs:
        if not LanguageRegistry.has(lang_code):
            continue
        l4_documents[lang_code] = [
            GeneratedDocument(
                filename=base,
                base_name=base,
                language_code=lang_code,
                content=content,
                word_count=len(content.split()),
            )
            for base, lang_contents in pages.items()
            if lang_code in lang_contents
            for content in [lang_contents[lang_code]]
        ]

    for passage in CrossLanguageReviewer().align_documents(l4_documents):
        present = [lang for lang, text in passage.texts.items() if text != "missing"]
        if len(present) >= 2 or any(text == "missing" for text in passage.texts.values()):
            review_pairs.append(
                {
                    "review_item_id": passage.review_item_id,
                    "document": passage.document_id,
                    "section_id": passage.section_id,
                    "block_id": passage.block_id,
                    "passages": passage.texts,
                }
            )

    alignment_ratio = (
        fully_aligned_pages / len(pages) if pages else 0.0
    )
    meets_threshold = alignment_ratio >= cfg.review.min_page_alignment_ratio

    if output_format == "json":
        typer.echo(json_lib.dumps({
            "review_pairs": review_pairs,
            "alignment_ratio": round(alignment_ratio, 3),
            "min_page_alignment_ratio": cfg.review.min_page_alignment_ratio,
            "meets_alignment_threshold": meets_threshold,
        }, indent=2, ensure_ascii=False))
    else:
        console.print("[bold]Semantic Review Data[/bold]")
        console.print(f"  Documents with multiple languages: {len(pages)}")
        console.print(f"  Section pairs for review: {len(review_pairs)}")
        for pair in review_pairs[:10]:
            console.print(f"\n  [cyan]{pair['document']}[/cyan] — {pair['section_id']}")
            passages = cast(dict[str, str], pair["passages"])
            for lang, text in passages.items():
                preview = str(text)[:80].replace("\n", " ")
                console.print(f"    [{lang}] {preview}...")


def _load_config(config_path: Path | None, target: Path) -> MakeWikiConfig:
    if config_path and config_path.is_file():
        return MakeWikiConfig.load(config_path, target)
    default_path = target / "makewiki.config.yaml"
    if default_path.is_file():
        return MakeWikiConfig.load(default_path, target)
    return MakeWikiConfig.default(target)


# --- verify-docs honest rendering helpers ------------------------------------


def _render_layer_status(status: str) -> str:
    """Render one layer's verdict with a DISTINCT marker per state.

    passed -> PASS, failed -> FAIL, pending -> PEND, not_applicable -> N/A.
    A pending layer is NEVER rendered as PASS.
    """
    marker: str
    color: str
    if status == "passed":
        marker, color = "PASS", "green"
    elif status == "failed":
        marker, color = "FAIL", "red"
    elif status == "pending":
        marker, color = "PEND", "yellow"
    elif status == "not_applicable":
        marker, color = "N/A", "dim"
    else:  # unknown / unexpected
        marker, color = "PEND", "yellow"
    return f"[{color}]{marker}[/{color}]"


def _render_gate_verdict(result: Any) -> str:
    """Render the honest gate verdict line with a distinct marker.

    PASS only when the verdict is genuinely ``passed`` — a pending gate is
    never printed PASS, regardless of the exit-policy CI code.
    """
    verdict = result.verdict
    if verdict == "passed":
        return "[green]PASS[/green] (passed)"
    if verdict == "failed":
        return "[red]FAIL[/red] (failed)"
    if verdict == "pending_mechanical_verification":
        return "[yellow]PEND[/yellow] (pending_mechanical_verification)"
    return "[yellow]PEND[/yellow] (pending_semantic_review)"


def _load_semantic_audit(
    semantic_audit: Path | None,
    resolved_wiki_dir: Path,
    semantic_model: Path | None = None,
) -> Any:
    """Load and validate an LLM SemanticAuditBundle, if requested.

    Returns the parsed bundle when it is present and still matches the verified
    documents and (if declared) can be bound to a supplied current semantic
    model; returns ``None`` when no bundle was requested, the bundle is
    stale/absent, OR the bundle declares a ``semantic_model_digest`` but no
    ``--semantic-model`` was supplied (model binding UNPROVEN) — so L3/L4b/L5
    stay PENDING at the gate. Diagnostics are written to stderr so the stdout
    (JSON payload or human table) stays clean.
    """
    if semantic_audit is None:
        return None
    from rich.console import Console as _StderrConsole

    from makewiki_skills.verification.semantic_audit import (
        bundle_matches_documents,
        load_audit_bundle,
    )

    err = _StderrConsole(stderr=True, highlight=False)

    audit_path = Path(semantic_audit).resolve()
    if not audit_path.is_file():
        err.print(f"[yellow]Semantic audit file not found: {audit_path}[/yellow]")
        err.print("[yellow]L3/L4b/L5 remain PENDING.[/yellow]")
        return None

    try:
        bundle = load_audit_bundle(audit_path)
    except ValueError as exc:
        err.print(f"[yellow]Invalid semantic audit bundle: {exc}[/yellow]")
        err.print("[yellow]L3/L4b/L5 remain PENDING.[/yellow]")
        return None

    doc_paths = sorted(resolved_wiki_dir.rglob("*.md"))
    if doc_paths and not bundle_matches_documents(bundle, doc_paths):
        err.print(
            "[yellow]Semantic audit bundle is stale (document digest mismatch).[/yellow]"
        )
        err.print(
            "[yellow]L3/L4b/L5 remain PENDING; the bundle is NOT merged.[/yellow]"
        )
        return None

    # Change 2 (CRITICAL honesty): the bundle declares a semantic_model_digest,
    # but no current semantic model was supplied -> the model binding is
    # UNPROVEN. Do NOT treat it as valid / merge it.
    if semantic_model is None and getattr(bundle, "semantic_model_digest", None):
        err.print(
            "[yellow]Semantic model binding UNPROVEN: the audit bundle declares "
            "semantic_model_digest but no --semantic-model was supplied.[/yellow]"
        )
        err.print("[yellow]L3/L4b/L5 remain PENDING; the bundle is NOT merged.[/yellow]")
        return None

    return bundle


def _load_semantic_model_digest(semantic_model: Path, err: Any) -> str | None:
    """Load + pydantic-validate a SemanticModel JSON and compute its canonical digest.

    Returns the canonical digest on success; prints a clear stderr diagnostic
    and returns ``None`` on validation failure so the caller keeps the relevant
    semantic audits pending (the bundle is NOT merged).
    """
    from makewiki_skills.model.semantic_model import SemanticModel
    from makewiki_skills.verification.semantic_audit import compute_content_digest

    model_path = Path(semantic_model).resolve()
    try:
        data = json_lib.loads(model_path.read_text(encoding="utf-8"))
        model = SemanticModel.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError / file errors
        err.print(f"[yellow]Invalid semantic model: {exc}[/yellow]")
        err.print(
            "[yellow]L3/L4b/L5 remain PENDING; the audit bundle is NOT merged.[/yellow]"
        )
        return None

    # Stable canonical form (sorted keys, compact separators) so the Auditor's
    # semantic_model_digest can be compared deterministically.
    canonical = json_lib.dumps(
        model.model_dump(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return compute_content_digest(canonical)


def _aggregate_key(check: Any) -> str:
    """Group key: (layer, claim_type, reason with quoted values normalized)."""
    detail = (check.detail or "").strip()
    normalized = re.sub(r"'[^']*'", "'…'", detail)
    normalized = re.sub(r"\s+", " ", normalized)
    return f"{check.layer}|{check.claim_type}|{normalized[:90]}"


def _render_aggregated(title: str, checks: list[Any], examples: int = 3) -> Table:
    """Render one summary row per group of same-kind findings.

    Presentation only: the JSON report keeps every individual finding.
    """
    groups: dict[str, list[Any]] = {}
    for check in checks:
        groups.setdefault(_aggregate_key(check), []).append(check)

    table = Table(title=title)
    table.add_column("Layer")
    table.add_column("Type")
    table.add_column("Count")
    table.add_column("Reason (representative)")
    table.add_column("Examples")
    for key in sorted(groups):
        items = groups[key]
        rep = items[0]
        reason = re.sub(r"\s+", " ", (rep.detail or ""))[:90]
        docs = ", ".join(sorted({rep.target for rep in items})[:3])
        if len(items) == 1:
            table.add_row(rep.layer, rep.claim_type, "1", reason, docs)
            continue
        example_lines = "\n".join(
            f"• {(c.claim_text or c.target)[:40]}" for c in items[:examples]
        )
        table.add_row(
            rep.layer,
            rep.claim_type,
            str(len(items)),
            reason,
            example_lines + (f"\n… +{len(items) - examples} more" if len(items) > examples else ""),
        )
    return table


def _render_check_table(title: str, checks: list[Any]) -> Table:
    """Render one status-section table with the standard L0-L5 columns."""
    table = Table(title=title)
    table.add_column("Layer")
    table.add_column("Document")
    table.add_column("Type")
    table.add_column("Claim")
    table.add_column("Detail")
    for check in checks:
        table.add_row(
            check.layer, check.target, check.claim_type, check.claim_text[:50], check.detail
        )
    return table


@app.command(name="build-site")
def build_site(
    makewiki_dir: Path = typer.Argument(..., help="Path to makewiki documentation directory"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for static site (defaults to <makewiki_dir>/site)",
    ),
    plan: Path | None = typer.Option(
        None,
        "--plan",
        "-p",
        help="Path to the LLM-authored SitePresentationPlan "
        "(defaults to <makewiki_dir>/site_presentation.json or .yaml)",
    ),
    theme: str = typer.Option(
        None, "--theme", help="Theme mode override: auto, light, dark (plan visual preferred)"
    ),
) -> None:
    """Compile generated Markdown into an offline static website (plan-driven).

    The site's Information Architecture (navigation, groups, ordering, page
    roles, hierarchy) comes solely from an LLM-authored SitePresentationPlan —
    the Main Agent / Site Designer is the only Site planning authority. The
    compiler renders that plan mechanically; it never derives IA from
    filenames. When no plan exists, the build is left unavailable/pending and
    exits cleanly rather than fabricating an Information Architecture.
    """
    from makewiki_skills.model.site_presentation import load_site_presentation
    from makewiki_skills.renderer.site_compiler import SiteCompiler

    makewiki_dir = Path(makewiki_dir).resolve()
    if not makewiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Documentation directory does not exist: {makewiki_dir}")
        raise typer.Exit(1)

    # Locate the LLM-authored plan: explicit --plan, else the conventional name
    # in the wiki directory. A missing plan is an "unavailable/pending" outcome,
    # never a fabricated IA — exit 0 so the Main Agent's cognitive work proceeds.
    plan_path = plan
    if plan_path is None:
        for candidate in ("site_presentation.json", "site_presentation.yaml", "site_presentation.yml"):
            probe = makewiki_dir / candidate
            if probe.is_file():
                plan_path = probe
                break
    if plan_path is None or not Path(plan_path).is_file():
        console.print(
            "[yellow]No SitePresentationPlan found — site build is pending.[/yellow] "
            "The Main Agent must author a SitePresentationPlan (e.g. "
            "<wiki_dir>/site_presentation.json) that declares project title, "
            "navigation, ordering, and visual direction. Build remains "
            "unavailable until then; cognitive work is not blocked."
        )
        raise typer.Exit(0)

    try:
        site_plan = load_site_presentation(plan_path)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Invalid SitePresentationPlan at {plan_path}: {exc}")
        raise typer.Exit(1)

    if theme:
        if theme not in ("auto", "light", "dark"):
            console.print(
                f"[red]Error:[/red] Invalid --theme {theme!r}; expected auto, light or dark."
            )
            raise typer.Exit(1)
        # A CLI --theme is an explicit mechanical override of the plan's visual
        # direction; the plan remains the authority for IA.
        site_plan.visual.theme = theme  # type: ignore[assignment]

    compiler = SiteCompiler(plan=site_plan)
    written = compiler.compile(makewiki_dir, output)
    console.print("[green]Static site compiled successfully![/green]")
    for path in written:
        console.print(f"  - {path}")


@app.command(name="census")
def census(
    target: Path = typer.Argument(..., help="Target project directory"),
    format_type: str = typer.Option("human", "--format", "-f", help="Output format: human, json"),
) -> None:
    """Extract raw verifiable facts from the repository (traits census)."""
    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Target directory does not exist: {target}")
        raise typer.Exit(1)

    source_ext_to_lang: dict[str, str] = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".scala": "scala",
        ".sh": "shell",
        ".bash": "shell",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".scss": "css",
        ".sass": "css",
        ".less": "css",
    }

    manifest_names = {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "package.json",
        "pnpm-lock.yaml",
        "pnpm-workspace.yaml",
        "yarn.lock",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "Gemfile",
        "composer.json",
        "CMakeLists.txt",
        "Makefile",
        "flake.nix",
    }

    entrypoint_names = {
        "main.py",
        "app.py",
        "cli.py",
        "index.ts",
        "index.js",
        "main.ts",
        "main.js",
        "main.rs",
        "main.go",
    }

    test_dir_names = {"tests", "test", "spec", "specs", "__tests__"}

    ignore_parts = {
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
        "target",
        "makewiki",
        ".makewiki",
        ".idea",
        ".vscode",
    }

    source_files: list[Path] = []
    doc_files: list[Path] = []
    manifests: list[str] = []
    entrypoints: list[str] = []
    configs: list[str] = []
    ci_and_infra: list[str] = []
    test_files: list[str] = []
    test_dirs: set[str] = set()
    tool_failures: list[str] = []

    try:
        for p in target.rglob("*"):
            if any(part in p.parts for part in ignore_parts):
                continue
            if p.is_dir():
                if p.name in test_dir_names:
                    try:
                        test_dirs.add(str(p.relative_to(target)).replace("\\", "/"))
                    except ValueError:
                        test_dirs.add(p.name)
                continue
            if not p.is_file():
                continue

            try:
                rel_str = str(p.relative_to(target)).replace("\\", "/")
            except ValueError:
                rel_str = p.name
            suffix = p.suffix.lower()
            name = p.name

            # Source files
            if suffix in source_ext_to_lang:
                source_files.append(p)
                if name in entrypoint_names or ("src" in p.parts and name in entrypoint_names):
                    entrypoints.append(rel_str)
                if (
                    name.startswith("test_")
                    or name.endswith("_test.py")
                    or name.endswith(".test.ts")
                    or name.endswith(".test.js")
                    or name.endswith(".spec.ts")
                    or name.endswith(".spec.js")
                    or name.endswith("_test.go")
                    or name.endswith("Test.java")
                ):
                    test_files.append(rel_str)

            # Doc files
            elif suffix in {".md", ".rst", ".adoc"}:
                doc_files.append(p)

            # Manifests
            if name in manifest_names:
                manifests.append(rel_str)

            # Configs
            if (
                name.startswith(".env")
                or name.endswith(".config.js")
                or name.endswith(".config.ts")
                or name.endswith(".config.yaml")
                or name.endswith(".config.yml")
                or name.endswith(".config.toml")
                or name in {"config.yaml", "config.yml", "config.toml", "config.json", "tsconfig.json"}
            ):
                configs.append(rel_str)

            # CI & Infra
            if (
                ".github/workflows" in rel_str
                or ".gitlab-ci.yml" in rel_str
                or "Dockerfile" in name
                or "docker-compose" in name
                or rel_str.startswith("k8s/")
                or rel_str.startswith("helm/")
            ):
                ci_and_infra.append(rel_str)

    except Exception as exc:
        tool_failures.append(f"Filesystem walk warning: {exc}")

    # Aggregations
    by_ext: dict[str, int] = {}
    by_lang: dict[str, int] = {}
    for sf in source_files:
        ext = sf.suffix.lower()
        by_ext[ext] = by_ext.get(ext, 0) + 1
        lang = source_ext_to_lang.get(ext, "other")
        by_lang[lang] = by_lang.get(lang, 0) + 1

    # Monorepo shape
    is_monorepo = False
    workspaces: list[str] = []
    for candidate_dir in ["packages", "apps", "libs", "crates", "modules"]:
        cdir = target / candidate_dir
        if cdir.is_dir():
            is_monorepo = True
            try:
                for sub in sorted(cdir.iterdir()):
                    if sub.is_dir():
                        workspaces.append(f"{candidate_dir}/{sub.name}")
            except Exception:
                pass

    # Detected ecosystems
    ecosystems: list[str] = []
    if "python" in by_lang or any("py" in m for m in manifests):
        ecosystems.append("python")
    if "typescript" in by_lang or "javascript" in by_lang or any("package.json" in m for m in manifests):
        ecosystems.append("node")
    if "rust" in by_lang or any("Cargo.toml" in m for m in manifests):
        ecosystems.append("rust")
    if "go" in by_lang or any("go.mod" in m for m in manifests):
        ecosystems.append("go")
    if "java" in by_lang or "kotlin" in by_lang or any("pom.xml" in m or "gradle" in m for m in manifests):
        ecosystems.append("jvm")
    if any("Docker" in f or "docker" in f for f in ci_and_infra):
        ecosystems.append("docker")
    if any(".github" in f for f in ci_and_infra):
        ecosystems.append("github_actions")

    data = {
        "project": target.name,
        "project_root": str(target),
        "source_files": len(source_files),
        "doc_files": len(doc_files),
        "languages": by_lang,
        "extensions": by_ext,
        "manifests": sorted(manifests),
        "entrypoints": sorted(entrypoints),
        "tests": {
            "test_files_count": len(test_files),
            "test_directories": sorted(test_dirs),
        },
        "configs": sorted(configs),
        "ci_and_infra": sorted(ci_and_infra),
        "monorepo_shape": {
            "is_monorepo": is_monorepo,
            "workspaces": workspaces,
        },
        "detected_ecosystems": ecosystems,
        "tool_failures_and_skips": {
            "failures": tool_failures,
        },
    }

    if format_type == "json":
        typer.echo(json_lib.dumps(data, indent=2, ensure_ascii=False))
    else:
        console.print(f"[bold]Project Fact Census: [cyan]{target.name}[/cyan][/bold]")
        console.print(f"  Source files: {len(source_files)}")
        console.print(f"  Doc files:    {len(doc_files)}")
        if by_lang:
            lang_summary = ", ".join(
                f"{lang}: {cnt}" for lang, cnt in sorted(by_lang.items(), key=lambda x: -x[1])
            )
            console.print(f"  Languages:    {lang_summary}")
        if manifests:
            console.print(
                f"  Manifests:    {', '.join(sorted(manifests)[:5])}{'...' if len(manifests) > 5 else ''}"
            )
        if entrypoints:
            console.print(
                f"  Entrypoints:  {', '.join(sorted(entrypoints)[:5])}{'...' if len(entrypoints) > 5 else ''}"
            )
        if test_dirs or test_files:
            console.print(
                f"  Tests:        {len(test_files)} test files, dirs: {', '.join(sorted(test_dirs)) or 'none'}"
            )
        if is_monorepo:
            console.print(f"  Monorepo:     yes ({len(workspaces)} workspaces)")
        if ecosystems:
            console.print(f"  Ecosystems:   {', '.join(ecosystems)}")
        if tool_failures:
            console.print(f"  [yellow]Warnings:     {len(tool_failures)} tool warnings recorded[/yellow]")


@app.command(name="sizing", hidden=True)
def sizing(
    target: Path = typer.Argument(..., help="Target project directory"),
    format_type: str = typer.Option("human", "--format", "-f", help="Output format: human, json"),
) -> None:
    """Deprecated alias for 'census'."""
    census(target=target, format_type=format_type)


@app.command(name="rebattle-diff")
def rebattle_diff(
    claims_files: list[Path] = typer.Argument(
        ..., help="Two or more JSON files containing ClaimSet data"
    ),
) -> None:
    """Compare Claims from multiple agents and output dispute/discrepancy matrix."""
    from makewiki_skills.model.rebattle import AgentClaimSet, ReBattleArena

    claim_sets: list[AgentClaimSet] = []
    for cf in claims_files:
        p = Path(cf).resolve()
        if not p.is_file():
            console.print(f"[red]Error:[/red] File does not exist: {p}")
            raise typer.Exit(1)
        data = json_lib.loads(p.read_text(encoding="utf-8"))
        claim_sets.append(AgentClaimSet.model_validate(data))

    discrepancies = ReBattleArena.detect_discrepancies(claim_sets)
    typer.echo(
        json_lib.dumps(
            {"discrepancies": [d.model_dump() for d in discrepancies]},
            indent=2,
            ensure_ascii=False,
        )
    )


@app.command()
def export(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ directory"),
    format_type: str = typer.Option(
        "all", "--format", "-f", help="Export format: all | html | epub"
    ),
    lang: str = typer.Option("en", "--lang", "-l", help="Language code to export"),
    title: str = typer.Option("Project Documentation", "--title", "-t", help="Document title"),
) -> None:
    """Export documentation into single-file HTML or EPUB bundles."""
    from makewiki_skills.renderer.exporter import DocExporter

    wiki_path = Path(wiki_dir).resolve()
    if not wiki_path.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {wiki_path}")
        raise typer.Exit(1)

    if format_type == "pdf":
        console.print("[red]Error:[/red] PDF export is not supported. Use --format html|epub|all.")
        raise typer.Exit(1)

    exporter = DocExporter(title=title)
    exported_files: list[Path] = []

    if format_type in ("all", "html"):
        html_file = exporter.export_pdf_ready_html(wiki_path, lang=lang)
        exported_files.append(html_file)
        console.print(f"[green]Compiled PDF-ready HTML:[/green] {html_file}")

    if format_type in ("all", "epub"):
        epub_file = exporter.export_epub(wiki_path, lang=lang)
        exported_files.append(epub_file)
        console.print(f"[green]Compiled EPUB e-book:[/green] {epub_file}")

    console.print(f"[bold green]Export complete! Total bundles: {len(exported_files)}[/bold green]")


@app.command(name="sync-bundle")
def sync_bundle(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ directory"),
    target_platform: str = typer.Option(
        "all", "--target", "-t", help="Target platform: all | confluence | notion"
    ),
    lang: str = typer.Option("en", "--lang", "-l", help="Language code to sync"),
    space_key: str = typer.Option("WIKI", "--space-key", help="Confluence space key"),
    parent_id: str = typer.Option("root", "--parent-id", help="Notion parent page ID"),
    push: bool = typer.Option(
        False,
        "--push",
        help="Reserved future flag: publish bundles to the target platform. Currently rejected.",
    ),
) -> None:
    """Prepare knowledge base sync bundles for Confluence or Notion.

    Note: this command only *prepares* the bundles (Confluence Storage XML /
    Notion Block API payloads) on disk. It does NOT publish or push anything to
    any external service.
    """
    from makewiki_skills.sync.confluence import ConfluenceSyncTool
    from makewiki_skills.sync.notion import NotionSyncTool

    if push:
        console.print(
            "[red]Error:[/red] --push is not implemented yet. sync-bundle is bundle-prep only."
        )
        raise typer.Exit(1)

    wiki_path = Path(wiki_dir).resolve()
    if not wiki_path.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {wiki_path}")
        raise typer.Exit(1)

    if target_platform in ("all", "confluence"):
        c_tool = ConfluenceSyncTool()
        c_bundle = c_tool.build_sync_bundle(wiki_path, space_key=space_key, lang=lang)
        console.print(f"[green]Generated Confluence Storage XML bundle:[/green] {c_bundle}")

    if target_platform in ("all", "notion"):
        n_tool = NotionSyncTool()
        n_bundle = n_tool.build_sync_bundle(wiki_path, parent_page_id=parent_id, lang=lang)
        console.print(f"[green]Generated Notion Block API payload bundle:[/green] {n_bundle}")

    console.print("[bold green]Knowledge base sync bundle preparation complete![/bold green]")


@app.command(name="sync")
def sync_alias(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ directory"),
    target_platform: str = typer.Option(
        "all", "--target", "-t", help="Target platform: all | confluence | notion"
    ),
    lang: str = typer.Option("en", "--lang", "-l", help="Language code to sync"),
    space_key: str = typer.Option("WIKI", "--space-key", help="Confluence space key"),
    parent_id: str = typer.Option("root", "--parent-id", help="Notion parent page ID"),
    push: bool = typer.Option(
        False,
        "--push",
        help="Reserved future flag: publish bundles to the target platform. Currently rejected.",
    ),
) -> None:
    """Deprecated alias for `sync-bundle`. Retained for backward compatibility."""
    sync_bundle(wiki_dir, target_platform, lang, space_key, parent_id, push=push)
