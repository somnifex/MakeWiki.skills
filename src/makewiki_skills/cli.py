"""Typer-based internal CLI for MakeWiki.skills.

This CLI serves the skill layer only. It is NOT a user-facing interface.
Skills invoke it via ``python -m makewiki_skills <command>``.
"""

from __future__ import annotations

import json as json_lib
from pathlib import Path
from typing import Any, Optional, cast

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

    if ctx.codebase_verification_report:
        cb_report = ctx.codebase_verification_report
        console.print(f"  Codebase verification: {cb_report.score:.1%} ({cb_report.verified_count}/{cb_report.total_checks})")
        if cb_report.failed_count:
            console.print(f"  [yellow]Failed checks: {cb_report.failed_count}[/yellow]")

    if ctx.validation_report:
        console.print(f"  Validation: {ctx.validation_report.summary()}")

@app.command()
def scan(
    target: Path = typer.Argument(..., help="Target project directory"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option("human", "--format", "-f", help="Output format: human | json"),
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

    if output_format == "json":
        if ctx.detection and ctx.evidence_registry:
            files_read: list[str] = []
            if ctx.collected_evidence:
                files_read = ctx.collected_evidence.raw_files_read
            bundle = ctx.evidence_registry.to_evidence_bundle(
                detection=ctx.detection,
                files_read=files_read,
            )
            typer.echo(json_lib.dumps(bundle.model_dump(), indent=2, ensure_ascii=False))
        else:
            typer.echo(json_lib.dumps({"error": "No evidence collected"}, indent=2))
        return

    # Human-readable output (default)
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
def verify(
    target: Path = typer.Argument(..., help="Target project directory"),
    wiki_dir: Optional[Path] = typer.Option(None, "--wiki-dir", "-w", help="Path to makewiki/ output (default: <target>/<output_dir>)"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    config_path: Optional[Path] = typer.Option(None, "--config", "-c"),
    output_format: str = typer.Option("human", "--format", "-f", help="Output format: human | json"),
) -> None:
    """Verify generated docs against the actual project codebase.

    Checks that file paths, commands, and config keys mentioned in the
    generated documentation actually exist in the project.
    """
    from makewiki_skills.generator.language_generator import GeneratedDocument
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

    # Load documents from disk
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
            docs.append(GeneratedDocument(
                filename=str(rel).replace("\\", "/"),
                base_name=base_name,
                language_code=lang_code,
                content=content,
                word_count=len(content.split()),
            ))
        documents[lang_code] = docs

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


@app.command(name="semantic-review")
def semantic_review(
    wiki_dir: Path = typer.Argument(..., help="Path to makewiki/ output directory"),
    langs: list[str] = typer.Option(["en", "zh-CN"], "--lang", "-l"),
    output_format: str = typer.Option("json", "--format", "-f", help="Output format: json | human"),
) -> None:
    """Output parallel passages from all language versions for LLM semantic review.

    Structures document content by section so the AI skill can compare
    semantics across languages. This is a data preparation tool, not an
    automated reviewer.
    """
    wiki_dir = Path(wiki_dir).resolve()
    if not wiki_dir.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {wiki_dir}")
        raise typer.Exit(1)

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
    for base_name, lang_contents in sorted(pages.items()):
        if len(lang_contents) < 2:
            continue

        ref_lang = next(iter(lang_contents))
        ref_sections = _split_by_h2(lang_contents[ref_lang])

        for section_heading in ref_sections:
            passages: dict[str, str] = {}
            for lang_code, content in lang_contents.items():
                sections = _split_by_h2(content)
                # Try to match by section index (headings differ across languages)
                section_idx = list(ref_sections.keys()).index(section_heading)
                other_sections = list(sections.values())
                if section_idx < len(other_sections):
                    passages[lang_code] = other_sections[section_idx][:500]
                else:
                    passages[lang_code] = ""

            if any(p.strip() for p in passages.values()):
                review_pairs.append({
                    "document": base_name,
                    "section_index": list(ref_sections.keys()).index(section_heading),
                    "reference_heading": section_heading,
                    "passages": passages,
                })

    if output_format == "json":
        typer.echo(json_lib.dumps({"review_pairs": review_pairs}, indent=2, ensure_ascii=False))
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
