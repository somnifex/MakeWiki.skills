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
            combined_lines: list[str] = []
            curr_cmd = ""
            for raw_line in block_lines:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    if curr_cmd:
                        combined_lines.append(curr_cmd.strip())
                        curr_cmd = ""
                    continue
                if line.startswith("$"):
                    line = line[1:].strip()
                if line.endswith("\\"):
                    curr_cmd += line[:-1].rstrip() + " "
                else:
                    if curr_cmd:
                        combined_lines.append((curr_cmd + line).strip())
                        curr_cmd = ""
                    else:
                        combined_lines.append(line)
            if curr_cmd:
                combined_lines.append(curr_cmd.strip())

            for line in combined_lines:
                if line:
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

    def extract_markdown_tables(self, content: str, source_path: str) -> list[EvidenceFact]:
        """Extract configuration and environment variable facts from markdown tables."""
        facts: list[EvidenceFact] = []
        table_rows = re.findall(r"^\|(.+)\|$", content, re.MULTILINE)
        if not table_rows:
            return facts

        in_config_table = False
        var_col_idx = -1
        desc_col_idx = -1

        for row in table_rows:
            cols = [c.strip() for c in row.split("|")]
            lower_cols = [c.lower() for c in cols]
            if any(
                k in " ".join(lower_cols)
                for k in ["variable", "config", "env", "key", "parameter", "变量"]
            ):
                in_config_table = True
                var_col_idx = next(
                    (
                        i
                        for i, c in enumerate(lower_cols)
                        if any(
                            k in c
                            for k in [
                                "variable",
                                "config",
                                "env",
                                "key",
                                "parameter",
                                "name",
                                "变量",
                                "配置项",
                            ]
                        )
                    ),
                    0,
                )
                desc_col_idx = next(
                    (
                        i
                        for i, c in enumerate(lower_cols)
                        if any(k in c for k in ["desc", "description", "meaning", "说明", "描述"])
                    ),
                    -1,
                )
                continue

            if all(re.match(r"^:?-+:?$", c) for c in cols if c):
                continue

            if in_config_table and 0 <= var_col_idx < len(cols):
                raw_var = cols[var_col_idx].strip(" `*")
                # Filter out invalid variable names, links, table headers, and markdown formatting
                if (
                    raw_var
                    and not raw_var.startswith("#")
                    and not raw_var.startswith("[")
                    and " " not in raw_var
                    and len(raw_var) >= 2
                    and re.match(r"^[A-Za-z0-9_.-]+$", raw_var)
                    and raw_var.lower()
                    not in {
                        "feature",
                        "requirement",
                        "resource",
                        "category",
                        "link",
                        "description",
                        "model",
                        "type",
                        "component",
                        "default",
                        "required",
                        "platform",
                        "variable",
                        "name",
                        "parameter",
                        "value",
                        "status",
                        "version",
                        "notes",
                        "action",
                        "role",
                    }
                ):
                    desc = cols[desc_col_idx] if 0 <= desc_col_idx < len(cols) else ""
                    facts.append(
                        EvidenceFact(
                            claim=f"Config/Env: {raw_var}" + (f" - {desc}" if desc else ""),
                            fact_type="config_key",
                            value=raw_var,
                            evidence=[
                                EvidenceLink(
                                    source_path=source_path,
                                    raw_text=row,
                                    confidence="high",
                                    extraction_method="table_extract",
                                )
                            ],
                        )
                    )
        return facts

    def extract_config_keys(
        self, data: dict[str, Any], source_path: str, prefix: str = ""
    ) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []

        # Special handling for Docker Compose files: extract clean environment variables and ports
        if prefix == "" and "services" in data and isinstance(data["services"], dict):
            for svc_name, svc_cfg in data["services"].items():
                if not isinstance(svc_cfg, dict):
                    continue
                # 1. Environment variables
                env_val = svc_cfg.get("environment")
                if isinstance(env_val, list):
                    for item in env_val:
                        if isinstance(item, str) and "=" in item:
                            k, v = item.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            facts.append(
                                EvidenceFact(
                                    claim=f"Docker Compose ({svc_name}) env: {k} (default: {v})",
                                    fact_type="config_key",
                                    value=k,
                                    evidence=[
                                        EvidenceLink(
                                            source_path=source_path,
                                            raw_text=f"{k}={v}",
                                            confidence="high",
                                            extraction_method="direct_read",
                                        )
                                    ],
                                )
                            )
                        elif isinstance(item, str) and item.strip():
                            k = item.strip()
                            facts.append(
                                EvidenceFact(
                                    claim=f"Docker Compose ({svc_name}) env: {k}",
                                    fact_type="config_key",
                                    value=k,
                                    evidence=[
                                        EvidenceLink(
                                            source_path=source_path,
                                            raw_text=k,
                                            confidence="high",
                                            extraction_method="direct_read",
                                        )
                                    ],
                                )
                            )
                elif isinstance(env_val, dict):
                    for k, v in env_val.items():
                        facts.append(
                            EvidenceFact(
                                claim=f"Docker Compose ({svc_name}) env: {k} (default: {v})",
                                fact_type="config_key",
                                value=str(k),
                                evidence=[
                                    EvidenceLink(
                                        source_path=source_path,
                                        raw_text=f"{k}: {v}",
                                        confidence="high",
                                        extraction_method="direct_read",
                                    )
                                ],
                            )
                        )
                # 2. Ports
                ports = svc_cfg.get("ports")
                if isinstance(ports, list):
                    for p in ports:
                        facts.append(
                            EvidenceFact(
                                claim=f"Docker Compose ({svc_name}) exposed port: {p}",
                                fact_type="config_key",
                                value=f"Port {p}",
                                evidence=[
                                    EvidenceLink(
                                        source_path=source_path,
                                        raw_text=f"ports: {p}",
                                        confidence="high",
                                        extraction_method="direct_read",
                                    )
                                ],
                            )
                        )
            return facts

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

    def extract_dependencies(self, deps: list[str], source_path: str) -> list[EvidenceFact]:
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
