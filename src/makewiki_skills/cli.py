"""Typer-based CLI for MakeWiki.skills."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from makewiki_skills.config import MakeWikiConfig

app = typer.Typer(
    name="makewiki",
    help="Generate multilingual user-facing wiki documentation for any software project.",
    add_completion=False,
)
console = Console()

@app.command()
def generate(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l", help="Languages to generate"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to makewiki.config.yaml"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output directory name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Generate multilingual wiki documentation for a project."""
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

    if ctx.validation_report:
        console.print(f"  Validation: {ctx.validation_report.summary()}")

@app.command()
def scan(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
) -> None:
    """Scan a project and output evidence summary (stages 1-2 only)."""
    from makewiki_skills.pipeline.pipeline import Pipeline

    target = Path(target).resolve()
    if not target.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {target}")
        raise typer.Exit(1)

    cfg = _load_config(config_path, target)
    pipeline = Pipeline(cfg)
    ctx = pipeline.run_until("collect_evidence")

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
    for ftype, count in sorted(summary.items()):
        table.add_row(ftype, str(count))
    console.print(table)
    console.print(f"Total facts: {len(ctx.evidence_registry)}")

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
        console.print(f"  [{severity_color}]{issue.severity}[/{severity_color}] {issue.issue_type}: {issue.message}")

    if report.passed:
        console.print("[green]Validation passed.[/green]")
    else:
        console.print("[red]Validation failed.[/red]")
        raise typer.Exit(1)

@app.command()
def review(
    target: Path = typer.Argument(..., help="Target project directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
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
            docs.append(GeneratedDocument(
                filename=str(rel).replace("\\", "/"),
                base_name=base_name,
                language_code=lang_code,
                content=content,
                word_count=len(content.split()),
            ))
        documents[lang_code] = docs

    reviewer = CrossLanguageReviewer()
    result = reviewer.review(documents)

    console.print(f"[bold]Cross-Language Review[/bold]")
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
            sev_color = {"critical": "red", "major": "yellow", "minor": "dim"}.get(delta.severity, "")
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

def _load_config(config_path: Path | None, target: Path) -> MakeWikiConfig:
    if config_path and config_path.is_file():
        return MakeWikiConfig.load(config_path, target)
    default_path = target / "makewiki.config.yaml"
    if default_path.is_file():
        return MakeWikiConfig.load(default_path, target)
    return MakeWikiConfig.default(target)
