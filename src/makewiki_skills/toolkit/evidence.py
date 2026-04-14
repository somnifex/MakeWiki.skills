"""Evidence models and helpers for extracting project facts."""

from __future__ import annotations

import re
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field

class EvidenceLink(BaseModel):
    """A pointer to a specific location in the project that supports a fact."""

    source_path: str  # relative to project root
    line_range: tuple[int, int] | None = None
    section: str | None = None
    raw_text: str
    confidence: Literal["high", "medium", "low", "inferred"] = "medium"
    extraction_method: str = "direct_read"

class EvidenceFact(BaseModel):
    """A single verifiable fact about the project, backed by evidence."""

    fact_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    claim: str
    fact_type: str  # "command" | "config_key" | "path" | "version" | "dependency" | "description"
    value: str | None = None
    evidence: list[EvidenceLink] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def best_confidence(self) -> str:
        """Return the highest confidence level from all evidence links."""
        order = {"high": 0, "medium": 1, "low": 2, "inferred": 3}
        if not self.evidence:
            return "inferred"
        return min(self.evidence, key=lambda e: order.get(e.confidence, 99)).confidence

class EvidenceTool:
    """Extract structured facts from text and config data."""

    name = "evidence"

    def extract_commands(self, content: str, source_path: str) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []
        lines = content.splitlines()
        current_heading: str | None = None
        in_code_block = False
        capture_commands = False
        block_section: str | None = None
        block_lines: list[str] = []

        def flush_block() -> None:
            if not capture_commands:
                return
            for raw_line in block_lines:
                line = raw_line.strip()
                if line.startswith("$"):
                    line = line[1:].strip()
                if line and not line.startswith("#"):
                    claim = (
                        f"Command from {block_section}: {line}"
                        if block_section
                        else f"Command: {line}"
                    )
                    facts.append(
                        EvidenceFact(
                            claim=claim,
                            fact_type="command",
                            value=line,
                            evidence=[
                                EvidenceLink(
                                    source_path=source_path,
                                    section=block_section,
                                    raw_text=line,
                                    confidence="medium",
                                    extraction_method="pattern_match",
                                )
                            ],
                        )
                    )

        for raw_line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", raw_line)
            if not in_code_block and heading_match:
                current_heading = heading_match.group(2).strip()
                continue

            fence_match = re.match(r"^```(\w*)\s*$", raw_line.strip())
            if fence_match:
                if in_code_block:
                    flush_block()
                    in_code_block = False
                    capture_commands = False
                    block_section = None
                    block_lines = []
                    continue

                in_code_block = True
                language = (fence_match.group(1) or "").lower()
                capture_commands = language in ("", "bash", "sh", "shell", "console")
                block_section = current_heading
                block_lines = []
                continue

            if in_code_block and capture_commands:
                block_lines.append(raw_line)

        return facts

    def extract_config_keys(
        self, data: dict[str, Any], source_path: str, prefix: str = ""
    ) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            facts.append(
                EvidenceFact(
                    claim=f"Config key: {full_key}",
                    fact_type="config_key",
                    value=full_key,
                    evidence=[
                        EvidenceLink(
                            source_path=source_path,
                            raw_text=f"{full_key} = {value!r}",
                            confidence="high",
                            extraction_method="direct_read",
                        )
                    ],
                )
            )
            if isinstance(value, dict):
                facts.extend(self.extract_config_keys(value, source_path, full_key))
        return facts

    def extract_version(self, content: str, source_path: str) -> EvidenceFact | None:
        match = re.search(r'(?:version|__version__)\s*[=:]\s*["\']([^"\']+)["\']', content)
        if match:
            return EvidenceFact(
                claim=f"Project version: {match.group(1)}",
                fact_type="version",
                value=match.group(1),
                evidence=[
                    EvidenceLink(
                        source_path=source_path,
                        raw_text=match.group(0),
                        confidence="high",
                        extraction_method="pattern_match",
                    )
                ],
            )
        return None

    def extract_dependencies(
        self, deps: list[str], source_path: str
    ) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []
        for dep in deps:
            name = re.split(r"[><=!~\[]", dep)[0].strip()
            if name:
                facts.append(
                    EvidenceFact(
                        claim=f"Dependency: {name}",
                        fact_type="dependency",
                        value=name,
                        evidence=[
                            EvidenceLink(
                                source_path=source_path,
                                raw_text=dep,
                                confidence="high",
                                extraction_method="direct_read",
                            )
                        ],
                    )
                )
        return facts

    @staticmethod
    def merge_facts(facts: list[EvidenceFact]) -> list[EvidenceFact]:
        seen: dict[str, EvidenceFact] = {}
        for fact in facts:
            key = f"{fact.fact_type}:{fact.value}"
            if key in seen:
                seen[key].evidence.extend(fact.evidence)
            else:
                seen[key] = fact.model_copy(deep=True)
        return list(seen.values())

    def execute(self, **kwargs: Any) -> Any:
        raise NotImplementedError("Use the typed extraction methods directly.")
