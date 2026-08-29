import json as json_lib
import sys
from pathlib import Path
from typing import Any, cast

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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


@app.command(name="deterministic-generate")
def deterministic_generate(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l", help="Languages to generate"),
    config_path: Path | None = typer.Option(
        None, "--config", "-c", help="Path to makewiki.config.yaml"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Deterministic scaffold generator — NOT the authoritative /makewiki path.

    This command drives Python's *mechanical* pipeline (extract evidence, build
    identity/installation/configuration/commands, render Jinja templates). It
    produces structurally grounded scaffolding but never invents semantic content
    (FAQ, troubleshooting, usage, workflows). The authoritative, LLM-driven flow is
    `/makewiki` in the Skill layer.
    """
    from makewiki_skills.pipeline.pipeline import Pipeline

    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Target directory does not exist: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    cfg.languages = langs
    if output:
        cfg.output_dir = output

    console.print(f"[bold]MakeWiki[/bold] generating docs for [cyan]{target.name}[/cyan]")
    console.print(f"  Languages: {', '.join(cfg.languages)}")
    console.print(f"  Output: {target / cfg.output_dir}")
    console.print()

    pipeline = Pipeline(cfg)
    ctx = pipeline.run()

    if ctx.errors:
        console.print("[red]Errors:[/red]")
        for err in ctx.errors:
            console.print(f"  - {err}")

    if ctx.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for w in ctx.warnings:
            console.print(f"  - {w}")

    console.print()
    console.print(f"[green]Done![/green] Written {len(ctx.written_files)} files")

    if verbose and ctx.stage_timings:
        table = Table(title="Stage Timings")
        table.add_column("Stage")
        table.add_column("Time (s)", justify="right")
        for name, t in ctx.stage_timings.items():
            table.add_row(name, f"{t:.3f}")
        console.print(table)

    if ctx.cross_language_review:
        review = ctx.cross_language_review
        console.print(f"  Cross-language consistency: {review.consistency_score:.1%}")
        if review.critical_issues:
            console.print(f"  [red]Critical issues: {len(review.critical_issues)}[/red]")

    if ctx.grounding_report:
        report = ctx.grounding_report
        console.print(f"  Grounding score: {report.grounding_score:.1%}")
        if report.violations:
            console.print(f"  [yellow]Ungrounded claims: {len(report.violations)}[/yellow]")

    if ctx.codebase_verification_report:
        cb_report = ctx.codebase_verification_report
        console.print(
            f"  Codebase verification: {cb_report.score:.1%} ({cb_report.verified_count}/{cb_report.total_checks})"
        )
        if cb_report.failed_count:
            console.print(f"  [yellow]Failed checks: {cb_report.failed_count}[/yellow]")

    if ctx.validation_report:
        console.print(f"  Validation: {ctx.validation_report.summary()}")


@app.command(name="generate")
def generate_alias(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l", help="Languages to generate"),
    config_path: Path | None = typer.Option(
        None, "--config", "-c", help="Path to makewiki.config.yaml"
    ),
    output: str | None = typer.Option(None, "--output", "-o", help="Output directory name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Deprecated alias for `deterministic-generate`.

    Retained for backward compatibility. It runs the same deterministic,
    non-authoritative scaffold pipeline. Prefer `deterministic-generate`; the
    authoritative, LLM-driven flow is `/makewiki` in the Skill layer.
    """
    deterministic_generate(target, langs, config_path, output, verbose)


@app.command(name="evidence")
def evidence(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Scan a project and emit the collected evidence facts.

    Emits *facts only* — deterministic extractions (commands, config keys,
    paths, versions) with their source evidence. Python never interprets what
    the repository *means*; that is the LLM's job.
    """
    from makewiki_skills.pipeline.pipeline import Pipeline

    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    pipeline = Pipeline(cfg)
    ctx = pipeline.run_until("verify_claims")

    if output_format == "json":
        if ctx.detection and ctx.evidence_registry:
            files_read: list[str] = []
            if ctx.collected_evidence:
                files_read = ctx.collected_evidence.raw_files_read
            claims_data = (
                [c.model_dump() for c in ctx.claim_set.claims]
                if ctx.claim_set
                else []
            )
            bundle = ctx.evidence_registry.to_evidence_bundle(
                detection=ctx.detection,
                files_read=files_read,
                claims=claims_data,
            )
            typer.echo(json_lib.dumps(bundle.model_dump(), indent=2, ensure_ascii=False))
        else:
            typer.echo(json_lib.dumps({"error": "No evidence collected"}, indent=2))
        return

    if ctx.detection:
        console.print(f"[bold]Project:[/bold] {ctx.detection.project_name}")
        console.print(f"[bold]Type:[/bold] {ctx.detection.project_type.value}")
        console.print(f"[bold]Confidence:[/bold] {ctx.detection.confidence:.0%}")
        console.print(f"[bold]Indicators:[/bold] {', '.join(ctx.detection.indicators_found)}")

    if ctx.claim_set:
        console.print(f"[bold]Claims Generated:[/bold] {len(ctx.claim_set.claims)}")

    console.print()
    summary = ctx.evidence_registry.to_summary()
    table = Table(title="Evidence Summary")
    table.add_column("Fact Type")
    table.add_column("Count", justify="right")
    for ftype, count in sorted(summary.items()):
        table.add_row(ftype, str(count))
    console.print(table)
    console.print(f"Total facts: {len(ctx.evidence_registry)}")


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


@app.command(name="verify-docs")
def verify_docs(
    target: Path = typer.Argument(..., help="Target project directory"),
    wiki_dir: Path | None = typer.Option(
        None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Run unified L0-L5 verification plus the Quality Gate on existing docs.

    Verifies that every claim in the generated documentation is grounded —
    paths exist (L1), interfaces/probes match (L2), behavior is evidenced
    (L3), languages agree (L4), and over-assertion is flagged (L5). The Quality
    Gate aggregates the layers into a PASS/FAIL decision mapped to the CI exit
    code (0 pass / 1 fail).
    """
    from makewiki_skills.generator.language_generator import GeneratedDocument
    from makewiki_skills.languages.registry import LanguageRegistry
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
    report = orchestrator.verify_documents(documents, wiki_dir=resolved_wiki_dir)
    result = evaluate_quality_gate(
        report, cfg, fail_on_critical=cfg.quality.fail_on_critical
    )

    if output_format == "json":
        typer.echo(
            json_lib.dumps(
                {"report": report.model_dump(), "quality_gate": result.model_dump()},
                indent=2,
                ensure_ascii=False,
            )
        )
        raise typer.Exit(result.exit_code)

    console.print("[bold]L0-L5 Verification[/bold]")
    for layer_name in ("L0", "L1", "L2", "L3", "L4", "L5"):
        layer_report = report.layers.get(layer_name)
        if layer_report is None:
            continue
        state = (
            "[green]passed[/green]"
            if layer_report.passed
            else "[red]failed[/red]"
        )
        console.print(
            f"  {layer_name} ({layer_report.name}): {state} "
            f"{layer_report.passed_count}/{layer_report.total_checks}"
        )

    console.print(f"[bold]Quality Gate:[/bold] Grounding score {result.grounding_score:.1%}")
    gate_mark = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
    console.print(f"  Gate verdict: {gate_mark}")
    if result.unresolved_critical:
        console.print(f"  [yellow]Unresolved critical: {result.unresolved_critical}[/yellow]")

    failures = [
        check
        for layer_report in report.layers.values()
        for check in layer_report.failures()
    ]
    if failures:
        table = Table(title="Failed Checks")
        table.add_column("Layer")
        table.add_column("Document")
        table.add_column("Type")
        table.add_column("Claim")
        table.add_column("Detail")
        for check in failures:
            table.add_row(
                check.layer, check.target, check.claim_type, check.claim_text[:50], check.detail
            )
        console.print(table)

    raise typer.Exit(result.exit_code)


@app.command(name="verify")
def verify_alias(
    target: Path = typer.Argument(..., help="Target project directory"),
    wiki_dir: Path | None = typer.Option(
        None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Deprecated alias for `verify-docs`.

    Retained for backward compatibility; runs the same unified L0-L5
    verification and Quality Gate.
    """
    verify_docs(target, wiki_dir, langs, config_path, output_format)


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
    on it, and reports each claim's per-layer verification status (L0-L5).
    This is the mechanical proof half of the Cognitive Authority Boundary:
    Python proves what it can (L0 syntax, L1 existence) and marks everything
    else pending for LLM judgment.
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
    from makewiki_skills.verification.orchestrator import VerificationOrchestrator
    from makewiki_skills.generator.language_generator import GeneratedDocument

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
    # H2 position like semantic-review does.
    pages: dict[str, dict[str, str]] = {}
    default_lang = langs[0] if langs else "en"
    for lang_code, doc_list in documents.items():
        for doc in doc_list:
            pages.setdefault(doc.base_name, {})[lang_code] = doc.content

    aligned: list[dict[str, Any]] = []
    for base_name, lang_contents in sorted(pages.items()):
        if len(lang_contents) < 2:
            continue
        ref_lang = next(iter(lang_contents))
        ref_sections = _split_by_h2(lang_contents[ref_lang])
        for section_heading in ref_sections:
            passages: dict[str, str] = {}
            ref_idx = list(ref_sections.keys()).index(section_heading)
            for lang_code, content in lang_contents.items():
                sections = _split_by_h2(content)
                other_sections = list(sections.values())
                if ref_idx < len(other_sections):
                    passages[lang_code] = other_sections[ref_idx][:800]
                else:
                    passages[lang_code] = ""
            if any(p.strip() for p in passages.values()):
                aligned.append({
                    "document": base_name,
                    "reference_heading": section_heading,
                    "passages": passages,
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
    console.print(f"[bold]Aligned passages:[/bold] {len(aligned)} section(s) ready for LLM prose review")
    raise typer.Exit(0 if l4_report.passed else 1)


@app.command()
def review(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Run cross-language review on existing makewiki output."""
    from makewiki_skills.generator.language_generator import GeneratedDocument
    from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer

    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs

    from makewiki_skills.languages.registry import LanguageRegistry

    LanguageRegistry.load_builtins()

    wiki_dir = target / cfg.output_dir
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
    if not cfg.review.enable_semantic_review:
        console.print("[yellow]semantic-review is disabled (review.enable_semantic_review=false).[/yellow]")
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

        ref_lang = next(iter(lang_contents))
        ref_sections = _split_by_h2(lang_contents[ref_lang])

        for section_heading in ref_sections:
            passages: dict[str, str] = {}
            for lang_code, content in lang_contents.items():
                sections = _split_by_h2(content)
                # Headings differ across languages, so sections are matched by position.
                section_idx = list(ref_sections.keys()).index(section_heading)
                other_sections = list(sections.values())
                if section_idx < len(other_sections):
                    passages[lang_code] = other_sections[section_idx][:500]
                else:
                    passages[lang_code] = ""

            if any(p.strip() for p in passages.values()):
                review_pairs.append(
                    {
                        "document": base_name,
                        "section_index": list(ref_sections.keys()).index(section_heading),
                        "reference_heading": section_heading,
                        "passages": passages,
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
            console.print(f"\n  [cyan]{pair['document']}[/cyan] — {pair['reference_heading']}")
            passages = cast(dict[str, str], pair["passages"])
            for lang, text in passages.items():
                preview = str(text)[:80].replace("\n", " ")
                console.print(f"    [{lang}] {preview}...")


def _split_by_h2(content: str) -> dict[str, str]:
    """Split markdown content into sections by H2 headings."""
    import re

    sections: dict[str, str] = {}
    current_heading = "(intro)"
    current_lines: list[str] = []

    for line in content.splitlines():
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            if current_lines:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines)

    return sections


def _load_config(config_path: Path | None, target: Path) -> MakeWikiConfig:
    if config_path and config_path.is_file():
        return MakeWikiConfig.load(config_path, target)
    default_path = target / "makewiki.config.yaml"
    if default_path.is_file():
        return MakeWikiConfig.load(default_path, target)
    return MakeWikiConfig.default(target)


@app.command(name="build-site")
def build_site(
    makewiki_dir: Path = typer.Argument(..., help="Path to makewiki documentation directory"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for static site (defaults to <makewiki_dir>/site)",
    ),
    theme: str = typer.Option("auto", "--theme", help="Theme mode: auto, light, dark"),
    title: str = typer.Option("Project Documentation", "--title", help="Site title"),
) -> None:
    """Compile generated Markdown documentation into an offline static website."""
    from makewiki_skills.renderer.site_compiler import SiteCompiler

    makewiki_dir = Path(makewiki_dir).resolve()
    if not makewiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Documentation directory does not exist: {makewiki_dir}")
        raise typer.Exit(1)

    compiler = SiteCompiler(theme=theme, title=title)
    written = compiler.compile(makewiki_dir, output)
    console.print("[green]Static site compiled successfully![/green]")
    for path in written:
        console.print(f"  - {path}")


@app.command(name="sizing")
def sizing(
    target: Path = typer.Argument(..., help="Target project directory"),
    format_type: str = typer.Option("human", "--format", "-f", help="Output format: human, json"),
) -> None:
    """Assess project complexity and recommend subagent budget (Tier S / M / L)."""
    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Target directory does not exist: {target}")
        raise typer.Exit(1)

    source_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp"}
    source_files = [
        p
        for p in target.rglob("*")
        if p.is_file()
        and p.suffix in source_exts
        and not any(part in p.parts for part in ["node_modules", ".git", ".venv", "dist", "build"])
    ]
    doc_files = [
        p
        for p in target.rglob("*.md")
        if p.is_file()
        and not any(part in p.parts for part in ["node_modules", ".git", ".venv", "makewiki"])
    ]

    source_count = len(source_files)
    doc_count = len(doc_files)

    if source_count < 15:
        tier = "Tier S"
        recommended_subagents = 2
        strategy = "Lightweight / Single-pass with prompt-based multi-perspective check"
        rebattle_rounds = 0
    elif source_count <= 80:
        tier = "Tier M"
        recommended_subagents = 4
        strategy = "Standard Multi-Agent (Scout + Red vs Blue ReBattle + Parallel Writers)"
        rebattle_rounds = 1
    else:
        tier = "Tier L"
        recommended_subagents = 8
        strategy = (
            "Deep Multi-Agent (Scout + Red/Blue/Green 3-Way ReBattle + Parallel Writers + Reviewer)"
        )
        rebattle_rounds = 2

    data = {
        "project": target.name,
        "source_files": source_count,
        "doc_files": doc_count,
        "tier": tier,
        "recommended_subagents": recommended_subagents,
        "rebattle_rounds": rebattle_rounds,
        "strategy": strategy,
    }

    if format_type == "json":
        typer.echo(json_lib.dumps(data, indent=2, ensure_ascii=False))
    else:
        console.print(f"[bold]Project Sizing & Subagent Budget: [cyan]{target.name}[/cyan][/bold]")
        console.print(f"  Source files: {source_count}")
        console.print(f"  Doc files:    {doc_count}")
        console.print(f"  Assessment:   [bold green]{tier}[/bold green]")
        console.print(f"  Subagents:    [yellow]{recommended_subagents} subagents max[/yellow]")
        console.print(f"  ReBattle:     {rebattle_rounds} round(s)")
        console.print(f"  Strategy:     {strategy}")


@app.command(name="rebattle-diff")
def rebattle_diff(
    claims_files: list[Path] = typer.Argument(
        ..., help="Two or more JSON files containing ClaimSet data"
    ),
) -> None:
    """Compare Claims from multiple agents and output dispute/discrepancy matrix."""
    from makewiki_skills.model.rebattle import ClaimSet, ReBattleArena

    claim_sets: list[ClaimSet] = []
    for cf in claims_files:
        p = Path(cf).resolve()
        if not p.is_file():
            console.print(f"[red]Error:[/red] File does not exist: {p}")
            raise typer.Exit(1)
        data = json_lib.loads(p.read_text(encoding="utf-8"))
        claim_sets.append(ClaimSet.model_validate(data))

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
