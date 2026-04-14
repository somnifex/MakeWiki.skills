"""Static analysis of Python source files to extract CLI help strings."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


class CLIHelpFact(BaseModel):
    """A help string extracted from CLI framework source code."""

    param_name: str
    help_text: str
    source_path: str
    line_number: int
    framework: str = "unknown"  # "typer" | "click" | "argparse"


class CLIHelpExtractor:
    """Extract help text from argparse, click, and typer source without executing.

    Uses regex-based static analysis — no imports or AST parsing required.
    """

    _TYPER_PATTERNS = [
        re.compile(
            r"typer\.(?:Option|Argument)\s*\([^)]*help\s*=\s*[\"']([^\"']+)[\"']",
            re.DOTALL,
        ),
        re.compile(
            r"(\w+)\s*:\s*\w+.*?=\s*typer\.(?:Option|Argument)\s*\([^)]*help\s*=\s*[\"']([^\"']+)[\"']",
            re.DOTALL,
        ),
    ]

    _CLICK_PATTERNS = [
        re.compile(
            r"@\w*\.(?:option|argument)\s*\(\s*[\"']([^\"']+)[\"'][^)]*help\s*=\s*[\"']([^\"']+)[\"']",
            re.DOTALL,
        ),
    ]

    _ARGPARSE_PATTERNS = [
        re.compile(
            r"add_argument\s*\(\s*[\"']([^\"']+)[\"'][^)]*help\s*=\s*[\"']([^\"']+)[\"']",
            re.DOTALL,
        ),
    ]

    def extract_from_file(self, path: Path) -> list[CLIHelpFact]:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        results: list[CLIHelpFact] = []
        rel_path = str(path)
        lines = content.splitlines()

        has_typer = "typer" in content
        has_click = "click" in content
        has_argparse = "argparse" in content

        if has_typer:
            results.extend(self._extract_typer(content, lines, rel_path))
        if has_click:
            results.extend(self._extract_click(content, lines, rel_path))
        if has_argparse:
            results.extend(self._extract_argparse(content, lines, rel_path))

        return results

    def _extract_typer(
        self, content: str, lines: list[str], rel_path: str
    ) -> list[CLIHelpFact]:
        results: list[CLIHelpFact] = []

        for match in self._TYPER_PATTERNS[0].finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            results.append(
                CLIHelpFact(
                    param_name=self._guess_param_name(content, match.start()),
                    help_text=match.group(1),
                    source_path=rel_path,
                    line_number=line_num,
                    framework="typer",
                )
            )

        for match in self._TYPER_PATTERNS[1].finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            results.append(
                CLIHelpFact(
                    param_name=match.group(1),
                    help_text=match.group(2),
                    source_path=rel_path,
                    line_number=line_num,
                    framework="typer",
                )
            )

        return results

    def _extract_click(
        self, content: str, lines: list[str], rel_path: str
    ) -> list[CLIHelpFact]:
        results: list[CLIHelpFact] = []
        for pattern in self._CLICK_PATTERNS:
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                results.append(
                    CLIHelpFact(
                        param_name=match.group(1),
                        help_text=match.group(2),
                        source_path=rel_path,
                        line_number=line_num,
                        framework="click",
                    )
                )
        return results

    def _extract_argparse(
        self, content: str, lines: list[str], rel_path: str
    ) -> list[CLIHelpFact]:
        results: list[CLIHelpFact] = []
        for pattern in self._ARGPARSE_PATTERNS:
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                results.append(
                    CLIHelpFact(
                        param_name=match.group(1),
                        help_text=match.group(2),
                        source_path=rel_path,
                        line_number=line_num,
                        framework="argparse",
                    )
                )
        return results

    @staticmethod
    def _guess_param_name(content: str, match_pos: int) -> str:
        """Try to find the parameter name from surrounding context."""
        before = content[max(0, match_pos - 200) : match_pos]
        # Look for `name: Type =` pattern
        name_match = re.search(r"(\w+)\s*:\s*\w+[^=]*=\s*$", before)
        if name_match:
            return name_match.group(1)
        return "unknown"

    def to_evidence_facts(self, facts: list[CLIHelpFact]) -> list[EvidenceFact]:
        evidence_facts: list[EvidenceFact] = []
        for fact in facts:
            evidence_facts.append(
                EvidenceFact(
                    claim=f"CLI help for {fact.param_name}: {fact.help_text[:80]}",
                    fact_type="cli_help",
                    value=fact.param_name,
                    evidence=[
                        EvidenceLink(
                            source_path=fact.source_path,
                            line_range=(fact.line_number, fact.line_number),
                            raw_text=fact.help_text,
                            confidence="high",
                            extraction_method="static_analysis",
                        )
                    ],
                )
            )
        return evidence_facts
