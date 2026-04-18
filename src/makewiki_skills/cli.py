"""Internal CLI for MakeWiki.skills."""

from __future__ import annotations

import json as json_lib
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.orchestration import PageArtifactAssembler, RunLayout, RunStore
from makewiki_skills.orchestration.store import PlannedArtifactFile
from makewiki_skills.pipeline.pipeline import Pipeline, PipelineContext
from makewiki_skills.renderer.output_manager import OutputFilePlan, OutputManager
from makewiki_skills.renderer.validator import OutputValidator
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType

app = typer.Typer(
    name="makewiki",
    help="Internal toolkit CLI for MakeWiki skills.",
    add_completion=False,
)
console = Console()


@app.command()
def generate(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l", help="Languages to generate"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to makewiki.config.yaml"
    ),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run the artifact-first pipeline.

    This command prepares/resumes a run, refreshes orchestration state, and
    assembles any already-written page artifacts into the output directory.
    """
    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Target directory does not exist: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    cfg.languages = langs
    if output:
        cfg.output_dir = output

    ctx = Pipeline(cfg).run()
    if ctx.errors:
        for err in ctx.errors:
            console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)

    if ctx.run_layout is not None:
        console.print(f"[bold]Run[/bold]: {ctx.run_layout.run_id}")
        console.print(f"[bold]State[/bold]: {ctx.run_layout.state_file}")
        console.print(f"[bold]Evidence[/bold]: {ctx.run_layout.evidence_index_file}")

    ready_jobs: list[Any] = []
    incomplete_run = False
    if ctx.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in ctx.warnings:
            console.print(f"  - {warning}")

    console.print(f"[green]Assembled[/green] {len(ctx.written_files)} file(s)")

    if ctx.state is not None:
        store = RunStore(cfg)
        ready_jobs = store.ready_jobs(ctx.state)
        incomplete_run = any(job.status != "done" for job in ctx.state.jobs)
        console.print(f"  Ready jobs: {len(ready_jobs)}")

    if ctx.validation_report is not None:
        console.print(f"  Validation: {ctx.validation_report.summary()}")
    if ctx.codebase_verification_report is not None:
        report = ctx.codebase_verification_report
        console.print(
            f"  Codebase verification: {report.score:.1%} ({report.verified_count}/{report.total_checks})"
        )
    if ctx.cross_language_review is not None:
        review = ctx.cross_language_review
        console.print(f"  Cross-language consistency: {review.consistency_score:.1%}")

    if verbose and ctx.stage_timings:
        table = Table(title="Stage Timings")
        table.add_column("Stage")
        table.add_column("Time (s)", justify="right")
        for name, timing in ctx.stage_timings.items():
            table.add_row(name, f"{timing:.3f}")
        console.print(table)

    if incomplete_run:
        console.print("[yellow]Run incomplete.[/yellow] Finish the remaining jobs before treating this as successful output.")
        raise typer.Exit(2)


@app.command()
def prepare(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option("json", "--format", "-f", help="json | human"),
    write_run: bool = typer.Option(
        True,
        "--write-run/--no-write-run",
        help="Persist objective evidence and initial run files or return them for agent-side writing",
    ),
) -> None:
    """Collect objective evidence and prepare or resume a run."""
    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    ctx = Pipeline(cfg).run_until("collect_evidence")
    if ctx.errors:
        for err in ctx.errors:
            console.print(f"[red]Error:[/red] {err}")
        raise typer.Exit(1)
    if ctx.detection is None or ctx.collected_evidence is None:
        console.print("[red]Error:[/red] Failed to collect evidence")
        raise typer.Exit(1)

    store = RunStore(cfg)
    layout, state, evidence_index, resumed, planned_files = store.prepare_run(
        ctx.detection,
        ctx.collected_evidence,
        persist=write_run,
    )
    ctx.run_layout = layout
    ctx.state = state
    ctx.evidence_index = evidence_index
    if resumed:
        ctx.warnings.append(f"Resumed existing run {layout.run_id}")

    scan_job_status = store.scan_job_status(ctx.state)
    llm_scan_required = scan_job_status in {"pending", "failed", "stale"}

    payload = {
        "run_id": ctx.run_layout.run_id,
        "run_dir": str(ctx.run_layout.run_root),
        "state_path": str(ctx.run_layout.state_file),
        "evidence_index_path": str(ctx.run_layout.evidence_index_file),
        "collection_mode": ctx.evidence_index.collection_mode,
        "fallback_reason": ctx.evidence_index.fallback_reason,
        "scan_job_status": scan_job_status,
        "llm_scan_required": llm_scan_required,
        "resumed": resumed,
        "warnings": ctx.warnings,
        "fact_summary": ctx.evidence_index.fact_summary,
        "shard_count": ctx.evidence_index.shard_count,
    }
    if not write_run:
        payload["write_mode"] = "agent"
        payload["files"] = [_serialize_planned_file(file) for file in planned_files]
    _emit_payload(payload, output_format)


@app.command()
def status(
    target: Path = typer.Argument(..., help="Target project directory"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option("json", "--format", "-f", help="json | human"),
    write_state: bool = typer.Option(
        True,
        "--write-state/--no-write-state",
        help="Persist refreshed state.json or return it for agent-side writing",
    ),
) -> None:
    """Refresh and report the current run state."""
    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    store = RunStore(cfg)
    layout = _resolve_layout(store, cfg, run_id)
    if layout is None:
        console.print("[red]Error:[/red] No prepared run found")
        raise typer.Exit(1)

    evidence_index = store.load_evidence_index(layout)
    state, semantic_index = store.refresh_state(layout, cfg.languages, persist=write_state)
    ready_jobs = store.ready_jobs(state, limit=25)
    scan_job_status = store.scan_job_status(state)
    payload = {
        "run_id": layout.run_id,
        "state_path": str(layout.state_file),
        "collection_mode": evidence_index.collection_mode,
        "fallback_reason": evidence_index.fallback_reason,
        "scan_job_status": scan_job_status,
        "llm_scan_required": scan_job_status in {"pending", "failed", "stale"},
        "semantic_index_exists": semantic_index is not None,
        "semantic_index_path": str(layout.semantic_index_file),
        "module_count": len(semantic_index.modules) if semantic_index is not None else 0,
        "workflow_count": len(semantic_index.workflows) if semantic_index is not None else 0,
        "page_count": len(semantic_index.pages) if semantic_index is not None else 0,
        "job_counts": state.job_counts,
        "ready_jobs": [
            {
                "job_id": job.job_id,
                "kind": job.kind,
                "status": job.status,
                "artifact_path": job.artifact_path,
                "attempt": job.attempt,
                "depends_on": job.depends_on,
            }
            for job in ready_jobs
        ],
    }
    if not write_state:
        payload["state_update"] = {
            "path": str(layout.state_file),
            "content": state.model_dump_json(indent=2),
        }
    _emit_payload(payload, output_format)


@app.command()
def assemble(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    run_id: Optional[str] = typer.Option(None, "--run-id"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option("json", "--format", "-f", help="json | human"),
    write_output: bool = typer.Option(
        True,
        "--write-output/--no-write-output",
        help="Write makewiki files or return the file plan for agent-side materialization",
    ),
) -> None:
    """Assemble final docs from page plans and per-language page artifacts."""
    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs

    store = RunStore(cfg)
    layout = _resolve_layout(store, cfg, run_id)
    if layout is None:
        console.print("[red]Error:[/red] No prepared run found")
        raise typer.Exit(1)

    state, _semantic_index = store.refresh_state(layout, cfg.languages, persist=write_output)
    assembler = PageArtifactAssembler(cfg)
    documents, warnings = assembler.assemble(layout, store)
    output_dir = target / cfg.output_dir

    manager = OutputManager(
        output_dir,
        overwrite=cfg.overwrite,
        delete_stale_files=cfg.delete_stale_files,
    )
    if not write_output:
        planned_files, stale_files = manager.plan_output_files(documents, cfg.default_language)
        payload = {
            "run_id": layout.run_id,
            "write_mode": "agent",
            "files": [_serialize_output_file(file) for file in planned_files],
            "stale_files": [str(path) for path in stale_files],
            "warnings": warnings,
            "job_counts": state.job_counts,
            "validation": None,
        }
        _emit_payload(payload, output_format)
        return

    written = manager.write_documents(documents)
    manager.write_index(documents, cfg.default_language)
    validation = OutputValidator(cfg.documentation_policy).validate(output_dir)

    payload = {
        "run_id": layout.run_id,
        "written_files": [str(path) for path in written],
        "warnings": warnings,
        "job_counts": state.job_counts,
        "validation": validation.summary(),
    }
    _emit_payload(payload, output_format)


@app.command()
def scan(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Scan a project and print the collected evidence."""
    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    pipeline = Pipeline(cfg)
    ctx = pipeline.run_until("collect_evidence")

    if output_format == "json":
        if ctx.detection and ctx.collected_evidence:
            typer.echo(
                json_lib.dumps(_build_scan_json_payload(ctx), indent=2, ensure_ascii=False)
            )
        else:
            typer.echo(json_lib.dumps({"error": "No evidence collected"}, indent=2))
        return

    if ctx.detection:
        console.print(f"[bold]Project:[/bold] {ctx.detection.project_name}")
        console.print(f"[bold]Type:[/bold] {ctx.detection.project_type.value}")
        console.print(f"[bold]Confidence:[/bold] {ctx.detection.confidence:.0%}")
        console.print(f"[bold]Indicators:[/bold] {', '.join(ctx.detection.indicators_found)}")

    console.print()
    summary = ctx.evidence_registry.to_summary()
    table = Table(title="Evidence Summary")
    table.add_column("Fact Type")
    table.add_column("Count", justify="right")
    for fact_type, count in sorted(summary.items()):
        table.add_row(fact_type, str(count))
    console.print(table)
    console.print(f"Total facts: {len(ctx.evidence_registry)}")


@app.command()
def validate(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ output directory"),
) -> None:
    """Validate an existing makewiki output directory."""
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


@app.command()
def verify(
    target: Path = typer.Argument(..., help="Target project directory"),
    wiki_dir: Optional[Path] = typer.Option(
        None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"
    ),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option(
        "human", "--format", "-f", help="Output format: human | json"
    ),
) -> None:
    """Verify generated docs against the actual project codebase."""
    from makewiki_skills.languages.registry import LanguageRegistry
    from makewiki_skills.verification.codebase_verifier import CodebaseVerifier

    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs

    LanguageRegistry.load_builtins()
    resolved_wiki_dir = Path(wiki_dir).resolve() if wiki_dir else target / cfg.output_dir
    if not resolved_wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Wiki directory not found: {resolved_wiki_dir}")
        raise typer.Exit(1)

    documents = _load_documents_from_output(resolved_wiki_dir, langs, cfg.default_language)
    verifier = CodebaseVerifier(target)
    report = verifier.verify(documents)

    if output_format == "json":
        typer.echo(json_lib.dumps(report.model_dump(), indent=2, ensure_ascii=False))
        return

    console.print("[bold]Codebase Verification[/bold]")
    console.print(f"  Score: {report.score:.1%} ({report.verified_count}/{report.total_checks})")
    console.print(f"  Passed: {report.verified_count}  Failed: {report.failed_count}")

    failures = report.failures()
    if failures:
        table = Table(title="Failed Checks")
        table.add_column("Document")
        table.add_column("Type")
        table.add_column("Claim")
        table.add_column("Detail")
        for check in failures:
            table.add_row(check.document, check.claim_type, check.claim_text[:50], check.detail)
        console.print(table)

    if report.passed:
        console.print("[green]All checks passed.[/green]")
    else:
        console.print(f"[yellow]{report.failed_count} check(s) failed.[/yellow]")


@app.command()
def review(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Run cross-language review on existing makewiki output."""
    from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer

    target = Path(target).resolve()
    cfg = _load_config(config_path, target)
    cfg.languages = langs

    wiki_dir = target / cfg.output_dir
    if not wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Wiki directory not found: {wiki_dir}")
        raise typer.Exit(1)

    documents = _load_documents_from_output(wiki_dir, langs, cfg.default_language)
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
    output_format: str = typer.Option("human", "--format", "-f", help="json | human"),
    write_file: bool = typer.Option(
        True,
        "--write/--no-write",
        help="Write makewiki.config.yaml or return its content for agent-side writing",
    ),
) -> None:
    """Generate a default makewiki.config.yaml in the target directory."""
    target = Path(target).resolve()
    cfg = MakeWikiConfig.default(target)
    cfg.languages = langs

    config_path = target / "makewiki.config.yaml"
    config_content = cfg.to_yaml()
    if write_file:
        config_path.write_text(config_content, encoding="utf-8")
        if output_format == "json":
            _emit_payload({"path": str(config_path), "written": True}, output_format)
        else:
            console.print(f"[green]Created[/green] {config_path}")
        return

    payload = {
        "path": str(config_path),
        "content": config_content,
        "written": False,
    }
    _emit_payload(payload, output_format)


@app.command(name="semantic-review")
def semantic_review(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ output directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json | human"),
) -> None:
    """Prepare aligned passages for cross-language semantic review."""
    wiki_dir = Path(wiki_dir).resolve()
    if not wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {wiki_dir}")
        raise typer.Exit(1)

    pages: dict[str, dict[str, str]] = {}
    default_lang = langs[0] if langs else "en"

    for md_file in sorted(wiki_dir.rglob("*.md")):
        if md_file.name == "index.md":
            continue
        rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")
        detected_lang = _detect_language_from_filename(rel, langs, default_lang)
        base = _strip_language_suffix(rel, detected_lang, default_lang)
        content = md_file.read_text(encoding="utf-8", errors="replace")
        pages.setdefault(base, {})[detected_lang] = content

    review_pairs: list[dict[str, Any]] = []
    for base_name, lang_contents in sorted(pages.items()):
        if len(lang_contents) < 2:
            continue

        ref_lang = next(iter(lang_contents))
        ref_sections = _split_by_h2(lang_contents[ref_lang])

        for section_heading in ref_sections:
            passages: dict[str, str] = {}
            for lang_code, content in lang_contents.items():
                sections = _split_by_h2(content)
                section_idx = list(ref_sections.keys()).index(section_heading)
                other_sections = list(sections.values())
                passages[lang_code] = other_sections[section_idx][:500] if section_idx < len(other_sections) else ""

            if any(passage.strip() for passage in passages.values()):
                review_pairs.append(
                    {
                        "document": base_name,
                        "section_index": list(ref_sections.keys()).index(section_heading),
                        "reference_heading": section_heading,
                        "passages": passages,
                    }
                )

    if output_format == "json":
        typer.echo(json_lib.dumps({"review_pairs": review_pairs}, indent=2, ensure_ascii=False))
    else:
        console.print("[bold]Semantic Review Data[/bold]")
        console.print(f"  Documents with multiple languages: {len(pages)}")
        console.print(f"  Section pairs for review: {len(review_pairs)}")
        for pair in review_pairs[:10]:
            console.print(f"\n  [cyan]{pair['document']}[/cyan] - {pair['reference_heading']}")
            passages = pair["passages"]
            for lang, text in passages.items():
                preview = str(text)[:80].replace("\n", " ")
                console.print(f"    [{lang}] {preview}...")


def _split_by_h2(content: str) -> dict[str, str]:
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


def _emit_payload(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        typer.echo(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        return
    for key, value in payload.items():
        console.print(f"[bold]{key}:[/bold] {value}")


def _serialize_output_file(file: OutputFilePlan) -> dict[str, str]:
    return _serialize_planned_file(file)


def _serialize_planned_file(file: OutputFilePlan | PlannedArtifactFile) -> dict[str, str]:
    return {
        "path": str(file.target),
        "relative_path": file.relative_path,
        "content": file.content,
    }


def _build_scan_json_payload(ctx: "PipelineContext") -> dict[str, Any]:
    files_read = ctx.collected_evidence.raw_files_read if ctx.collected_evidence else []
    detection = ctx.detection
    if detection is None:
        target_dir = ctx.config.target_dir.resolve()
        detection = ProjectDetectionResult(
            project_type=ProjectType.GENERIC,
            confidence=0.0,
            project_name=target_dir.name,
            project_dir=str(target_dir),
        )
    bundle = ctx.evidence_registry.to_evidence_bundle(
        detection=detection,
        files_read=files_read,
    )
    collection_mode = ctx.collected_evidence.collection_mode if ctx.collected_evidence else "python"
    llm_scan_required = ctx.scan_fallback_required or collection_mode == "llm-fallback"
    fallback_reason = ctx.scan_failure_reason
    if not fallback_reason and ctx.collected_evidence is not None:
        fallback_reason = ctx.collected_evidence.fallback_reason

    scan_status = "fallback_required" if llm_scan_required else "complete"
    payload = bundle.model_dump()
    payload.update(
        {
            "scan_status": scan_status,
            "collection_mode": collection_mode,
            "llm_scan_required": llm_scan_required,
            "fallback_reason": fallback_reason,
            "warnings": ctx.warnings,
            "suggested_job_kind": "llm-scan" if llm_scan_required else None,
            "suggested_skill": "makewiki-llm-scan" if llm_scan_required else None,
            "next_step": (
                "Use the `makewiki-llm-scan` child skill to write objective evidence shards "
                "and update evidence.index.json before semantic orchestration."
                if llm_scan_required
                else None
            ),
        }
    )
    return payload


def _resolve_layout(store: RunStore, config: MakeWikiConfig, run_id: str | None) -> RunLayout | None:
    if run_id:
        layout = RunLayout.create(config.target_dir.resolve(), config.orchestration.state_dir, run_id)
        return layout if layout.state_file.is_file() else None
    return store.latest_layout()


def _load_documents_from_output(
    wiki_dir: Path,
    langs: list[str],
    default_language: str,
) -> dict[str, list["GeneratedDocument"]]:
    documents: dict[str, list[GeneratedDocument]] = {lang: [] for lang in langs}
    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name == "index.md":
            continue
        rel = str(md_file.relative_to(wiki_dir)).replace("\\", "/")
        language = _detect_language_from_filename(rel, langs, default_language)
        if language not in documents:
            documents[language] = []
        base_name = _strip_language_suffix(rel, language, default_language)
        content = md_file.read_text(encoding="utf-8", errors="replace")
        documents[language].append(
            GeneratedDocument(
                filename=rel,
                base_name=base_name,
                language_code=language,
                content=content,
                word_count=len(content.split()),
            )
        )
    return documents


def _detect_language_from_filename(path_text: str, langs: list[str], default_language: str) -> str:
    for lang in langs:
        if lang == default_language:
            continue
        if f".{lang}." in path_text:
            return lang
    return default_language


def _strip_language_suffix(path_text: str, language: str, default_language: str) -> str:
    if language == default_language:
        return path_text
    return path_text.replace(f".{language}.", ".", 1)


def _load_config(config_path: Path | None, target: Path) -> MakeWikiConfig:
    if config_path and config_path.is_file():
        return MakeWikiConfig.load(config_path, target)
    default_path = target / "makewiki.config.yaml"
    if default_path.is_file():
        return MakeWikiConfig.load(default_path, target)
    return MakeWikiConfig.default(target)
