"""Unit tests for L2 Interface Verifier."""

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.verification.l2_interface import L2InterfaceVerifier


def test_l2_valid_cli_flags_pass(tmp_path: Path):
    # Create sample CLI app source file
    cli_code = """
import typer

app = typer.Typer()

@app.command()
def scan(
    target: str,
    output_format: str = typer.Option("human", "--format", "-f", help="Format: human | json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    pass
"""
    (tmp_path / "cli.py").write_text(cli_code, encoding="utf-8")

    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nscan . --format json --verbose\n```\n",
    )
    verifier = L2InterfaceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert report.layer == "L2"
    assert report.passed
    assert all(c.verified for c in report.checks if c.claim_type == "interface")


def test_l2_invalid_flag_fails(tmp_path: Path):
    cli_code = """
import typer

app = typer.Typer()

@app.command()
def scan(target: str):
    pass
"""
    (tmp_path / "cli.py").write_text(cli_code, encoding="utf-8")

    doc = GeneratedDocument(
        filename="usage.md",
        base_name="usage.md",
        language_code="en",
        content="# Usage\n```bash\nscan . --unrecognized-flag value\n```\n",
    )
    verifier = L2InterfaceVerifier(tmp_path)
    report = verifier.verify_documents({"en": [doc]})

    assert not report.passed
    assert any(
        not c.verified and "--unrecognized-flag" in c.claim_text
        for c in report.checks
    )
