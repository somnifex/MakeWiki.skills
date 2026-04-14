"""Extract user-visible error messages from source code."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


class ErrorStringFact(BaseModel):
    """An error message extracted from source code."""

    message: str
    error_type: str  # "runtime_error" | "usage_error" | "exit_message" | "log_error"
    source_path: str
    line_number: int


class ErrorStringExtractor:
    """Find user-visible error messages in Python source code.

    Extracts strings from ``raise``, ``sys.exit``, ``console.print("[red]...")``,
    and ``logger.error(...)`` patterns.
    """

    _PATTERNS: list[tuple[re.Pattern[str], str]] = [
        (
            re.compile(r"raise\s+\w*(?:Error|Exception)\s*\(\s*(?:f?)[\"']([^\"']{10,})[\"']"),
            "runtime_error",
        ),
        (
            re.compile(r"sys\.exit\s*\(\s*(?:f?)[\"']([^\"']{5,})[\"']"),
            "exit_message",
        ),
        (
            re.compile(r"(?:typer|click)\.(?:BadParameter|UsageError|Abort)\s*\(\s*(?:f?)[\"']([^\"']{5,})[\"']"),
            "usage_error",
        ),
        (
            re.compile(r"console\.print\s*\(\s*(?:f?)[\"']\[red\]([^\"']{5,})[\"']"),
            "log_error",
        ),
        (
            re.compile(r"(?:logger|logging)\.(?:error|critical|warning)\s*\(\s*(?:f?)[\"']([^\"']{10,})[\"']"),
            "log_error",
        ),
        (
            re.compile(r"print\s*\(\s*(?:f?)[\"']((?:Error|Warning|Failed)[^\"']{5,})[\"']"),
            "log_error",
        ),
    ]

    def extract_from_file(self, path: Path) -> list[ErrorStringFact]:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        results: list[ErrorStringFact] = []
        rel_path = str(path)

        for pattern, error_type in self._PATTERNS:
            for match in pattern.finditer(content):
                line_num = content[: match.start()].count("\n") + 1
                message = match.group(1).strip()
                # Skip f-string placeholders that are mostly variable
                if message.count("{") > len(message) / 4:
                    continue
                results.append(
                    ErrorStringFact(
                        message=message,
                        error_type=error_type,
                        source_path=rel_path,
                        line_number=line_num,
                    )
                )

        return results

    def to_evidence_facts(self, facts: list[ErrorStringFact]) -> list[EvidenceFact]:
        evidence_facts: list[EvidenceFact] = []
        for fact in facts:
            evidence_facts.append(
                EvidenceFact(
                    claim=f"Error message ({fact.error_type}): {fact.message[:80]}",
                    fact_type="error_message",
                    value=fact.message,
                    evidence=[
                        EvidenceLink(
                            source_path=fact.source_path,
                            line_range=(fact.line_number, fact.line_number),
                            raw_text=fact.message,
                            confidence="high",
                            extraction_method="static_analysis",
                        )
                    ],
                )
            )
        return evidence_facts
