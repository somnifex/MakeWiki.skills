"""Tests for ErrorStringExtractor."""

from pathlib import Path
from textwrap import dedent

import pytest

from makewiki_skills.toolkit.error_extractor import ErrorStringExtractor


@pytest.fixture
def extractor() -> ErrorStringExtractor:
    return ErrorStringExtractor()


class TestRuntimeErrors:
    def test_raise_value_error(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "app.py"
        src.write_text(dedent("""\
            def validate(x):
                if x < 0:
                    raise ValueError("Input value must be non-negative")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 1
        assert facts[0].error_type == "runtime_error"
        assert "non-negative" in facts[0].message

    def test_raise_custom_error(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "core.py"
        src.write_text(dedent("""\
            class ConfigError(Exception):
                pass

            def load():
                raise ConfigError("Configuration file not found at expected path")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 1
        assert "Configuration file not found" in facts[0].message


class TestSysExit:
    def test_sys_exit_message(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "main.py"
        src.write_text(dedent("""\
            import sys
            def main():
                sys.exit("Error: unable to connect to database")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 1
        assert facts[0].error_type == "exit_message"
        assert "database" in facts[0].message


class TestLogErrors:
    def test_rich_console_error(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "cli.py"
        src.write_text(dedent("""\
            from rich.console import Console
            console = Console()
            console.print("[red]Error: target directory does not exist")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 1
        assert "target directory" in facts[0].message

    def test_logger_error(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "service.py"
        src.write_text(dedent("""\
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Failed to process request: invalid token format")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 1
        assert "invalid token" in facts[0].message


class TestPrintErrors:
    def test_print_error(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "script.py"
        src.write_text(dedent("""\
            print("Error: missing required argument --config")
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 1
        assert "missing required" in facts[0].message


class TestNoErrors:
    def test_clean_file(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "utils.py"
        src.write_text(dedent("""\
            def add(a, b):
                return a + b
        """))
        facts = extractor.extract_from_file(src)
        assert len(facts) == 0

    def test_short_error_strings_skipped(self, extractor: ErrorStringExtractor, tmp_path: Path) -> None:
        src = tmp_path / "tiny.py"
        src.write_text('raise ValueError("bad")\n')
        # "bad" is only 3 chars, below the 10-char minimum in the regex
        facts = extractor.extract_from_file(src)
        assert len(facts) == 0


class TestToEvidenceFacts:
    def test_converts_to_evidence_facts(self, extractor: ErrorStringExtractor) -> None:
        from makewiki_skills.toolkit.error_extractor import ErrorStringFact

        raw_facts = [
            ErrorStringFact(
                message="Config file not found",
                error_type="runtime_error",
                source_path="app.py",
                line_number=10,
            )
        ]
        evidence = extractor.to_evidence_facts(raw_facts)
        assert len(evidence) == 1
        assert evidence[0].fact_type == "error_message"
        assert evidence[0].value == "Config file not found"
