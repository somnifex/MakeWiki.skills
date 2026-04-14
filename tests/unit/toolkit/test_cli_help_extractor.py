"""Tests for CLIHelpExtractor."""

from pathlib import Path
from textwrap import dedent

import pytest

from makewiki_skills.toolkit.cli_help_extractor import CLIHelpExtractor


@pytest.fixture
def extractor() -> CLIHelpExtractor:
    return CLIHelpExtractor()


class TestTyperExtraction:
    def test_typer_option_help(self, extractor: CLIHelpExtractor, tmp_path: Path) -> None:
        src = tmp_path / "cli.py"
        src.write_text(dedent("""\
            import typer

            app = typer.Typer()

            @app.command()
            def run(
                port: int = typer.Option(8080, "--port", "-p", help="HTTP listen port"),
                verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
            ):
                pass
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) >= 2
        help_texts = [f.help_text for f in facts]
        assert "HTTP listen port" in help_texts
        assert "Enable verbose output" in help_texts
        assert all(f.framework == "typer" for f in facts)

    def test_typer_argument_help(self, extractor: CLIHelpExtractor, tmp_path: Path) -> None:
        src = tmp_path / "main.py"
        src.write_text(dedent("""\
            import typer
            app = typer.Typer()

            @app.command()
            def convert(
                input_file: str = typer.Argument(..., help="Path to input file"),
            ):
                pass
        """))
        facts = extractor.extract_from_file(src)
        assert any("Path to input file" in f.help_text for f in facts)


class TestClickExtraction:
    def test_click_option_help(self, extractor: CLIHelpExtractor, tmp_path: Path) -> None:
        src = tmp_path / "app.py"
        src.write_text(dedent("""\
            import click

            @click.command()
            @click.option("--output", "-o", help="Output directory path")
            def main(output):
                pass
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) >= 1
        assert facts[0].help_text == "Output directory path"
        assert facts[0].param_name == "--output"
        assert facts[0].framework == "click"


class TestArgparseExtraction:
    def test_argparse_help(self, extractor: CLIHelpExtractor, tmp_path: Path) -> None:
        src = tmp_path / "tool.py"
        src.write_text(dedent("""\
            import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument("--config", help="Path to config file")
            parser.add_argument("--dry-run", help="Show what would be done without making changes")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 2
        assert facts[0].param_name == "--config"
        assert facts[0].framework == "argparse"


class TestNoFramework:
    def test_no_cli_framework(self, extractor: CLIHelpExtractor, tmp_path: Path) -> None:
        src = tmp_path / "utils.py"
        src.write_text("def helper(): pass\n")
        facts = extractor.extract_from_file(src)
        assert len(facts) == 0


class TestToEvidenceFacts:
    def test_converts_to_evidence_facts(self, extractor: CLIHelpExtractor) -> None:
        from makewiki_skills.toolkit.cli_help_extractor import CLIHelpFact

        raw_facts = [
            CLIHelpFact(
                param_name="--port",
                help_text="HTTP listen port",
                source_path="cli.py",
                line_number=5,
                framework="typer",
            )
        ]
        evidence = extractor.to_evidence_facts(raw_facts)
        assert len(evidence) == 1
        assert evidence[0].fact_type == "cli_help"
        assert evidence[0].value == "--port"
