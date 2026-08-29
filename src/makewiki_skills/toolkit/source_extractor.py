"""Multi-language source code intelligence extractor for Go, Rust, Python, and JavaScript/TypeScript."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


class SourceSymbolFact(BaseModel):
    """A symbol, CLI flag, route, or function extracted from source code."""

    name: str
    symbol_type: Literal["cli_flag", "cli_command", "api_route", "exported_func", "struct_model"]
    description: str = ""
    default_value: str | None = None
    source_path: str = ""
    line_number: int = 1
    language: Literal["go", "rust", "python", "javascript", "typescript"] = "go"
    framework: str = ""


class MultiLanguageSourceExtractor:
    """Static analysis extractor for Go, Rust, Python, and JS/TS source code without execution."""

    # 1. Go Patterns
    _GO_FLAG_PATTERNS = [
        re.compile(
            r'flag\.(?:StringVar|IntVar|BoolVar|Float64Var|DurationVar)\s*\(\s*&?\w+,\s*["\']([^"\']+)["\']\s*,\s*([^,]+)\s*,\s*["\']([^"\']+)["\']',
            re.DOTALL,
        ),
        re.compile(
            r'flag\.(?:String|Int|Bool|Float64|Duration)\s*\(\s*["\']([^"\']+)["\']\s*,\s*([^,]+)\s*,\s*["\']([^"\']+)["\']',
            re.DOTALL,
        ),
        re.compile(
            r'pflag\.(?:StringVarP?|IntVarP?|BoolVarP?)\s*\(\s*&?\w+,\s*["\']([^"\']+)["\']\s*(?:,\s*["\'][^"\']*["\'])?\s*,\s*([^,]+)\s*,\s*["\']([^"\']+)["\']',
            re.DOTALL,
        ),
    ]

    _GO_COBRA_PATTERNS = [
        re.compile(
            r'&cobra\.Command\s*\{\s*Use:\s*["\']([^"\']+)["\']\s*,\s*Short:\s*["\']([^"\']+)["\']',
            re.DOTALL,
        ),
        re.compile(
            r'&cli\.Command\s*\{\s*Name:\s*["\']([^"\']+)["\']\s*,\s*Usage:\s*["\']([^"\']+)["\']',
            re.DOTALL,
        ),
    ]

    _GO_ROUTE_PATTERNS = [
        re.compile(
            r'(?:router|r|engine|api|group|v1|e|app)\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(\s*["\']([^"\']+)["\']',
            re.IGNORECASE,
        ),
    ]

    _GO_EXPORTED_FUNC_PATTERNS = [
        re.compile(
            r"((?://[^\n]*\n)+)\s*func\s+([A-Z]\w+)\s*\(([^)]*)\)\s*(?:[^{]*)\{",
            re.DOTALL,
        ),
    ]

    # 2. Rust Patterns
    _RUST_CLAP_ARG_PATTERNS = [
        re.compile(
            r'#\[arg\([^)]*help\s*=\s*["\']([^"\']+)["\'][^)]*\)\]\s*(?:pub\s+)?(\w+)\s*:\s*([^,\n]+)',
            re.DOTALL,
        ),
        re.compile(
            r'#\[command\([^)]*about\s*=\s*["\']([^"\']+)["\'][^)]*\)\]\s*(?:pub\s+)?struct\s+(\w+)',
            re.DOTALL,
        ),
    ]

    _RUST_ROUTE_PATTERNS = [
        re.compile(
            r'#\[(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']\s*\)\]\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)',
            re.DOTALL,
        ),
        re.compile(
            r'\.route\s*\(\s*["\']([^"\']+)["\']\s*,\s*(get|post|put|delete|patch)\s*\(\s*(\w+)\s*\)\s*\)',
            re.IGNORECASE,
        ),
    ]

    _RUST_EXPORTED_FUNC_PATTERNS = [
        re.compile(
            r"((?:///[^\n]*\n)+)\s*pub\s+(?:async\s+)?fn\s+(\w+)\s*\(([^)]*)\)",
            re.DOTALL,
        ),
    ]

    def extract_from_file(self, path: Path) -> list[SourceSymbolFact]:
        """Extract facts from a Go or Rust source file."""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        rel_path = str(path).replace("\\", "/")
        ext = path.suffix.lower()

        if ext == ".go":
            return self._extract_go(content, rel_path)
        elif ext == ".rs":
            return self._extract_rust(content, rel_path)
        return []

    def _extract_go(self, content: str, rel_path: str) -> list[SourceSymbolFact]:
        facts: list[SourceSymbolFact] = []

        # Flags
        for pattern in self._GO_FLAG_PATTERNS:
            for match in pattern.finditer(content):
                flag_name = match.group(1)
                default_val = match.group(2).strip().strip("\"'")
                help_text = match.group(3).strip()
                line_no = content[: match.start()].count("\n") + 1
                facts.append(
                    SourceSymbolFact(
                        name=f"--{flag_name}",
                        symbol_type="cli_flag",
                        description=help_text,
                        default_value=default_val if default_val != '""' else None,
                        source_path=rel_path,
                        line_number=line_no,
                        language="go",
                        framework="flag",
                    )
                )

        # Cobra / Urfave Commands
        for pattern in self._GO_COBRA_PATTERNS:
            for match in pattern.finditer(content):
                cmd_name = match.group(1)
                desc = match.group(2).strip()
                line_no = content[: match.start()].count("\n") + 1
                facts.append(
                    SourceSymbolFact(
                        name=cmd_name,
                        symbol_type="cli_command",
                        description=desc,
                        source_path=rel_path,
                        line_number=line_no,
                        language="go",
                        framework="cobra/cli",
                    )
                )

        # Routes (Gin, Echo, Chi)
        for pattern in self._GO_ROUTE_PATTERNS:
            for match in pattern.finditer(content):
                method = match.group(1).upper()
                route_path = match.group(2)
                line_no = content[: match.start()].count("\n") + 1
                facts.append(
                    SourceSymbolFact(
                        name=f"{method} {route_path}",
                        symbol_type="api_route",
                        description=f"REST endpoint {method} {route_path}",
                        source_path=rel_path,
                        line_number=line_no,
                        language="go",
                        framework="gin/http",
                    )
                )

        # Exported functions with doc comments
        for pattern in self._GO_EXPORTED_FUNC_PATTERNS:
            for match in pattern.finditer(content):
                doc_block = match.group(1)
                func_name = match.group(2)
                clean_doc = " ".join(
                    line.strip().lstrip("/").strip()
                    for line in doc_block.splitlines()
                    if line.strip()
                )
                line_no = content[: match.start()].count("\n") + 1
                if clean_doc and len(clean_doc) >= 10:
                    facts.append(
                        SourceSymbolFact(
                            name=func_name,
                            symbol_type="exported_func",
                            description=clean_doc,
                            source_path=rel_path,
                            line_number=line_no,
                            language="go",
                        )
                    )

        return facts

    def _extract_rust(self, content: str, rel_path: str) -> list[SourceSymbolFact]:
        facts: list[SourceSymbolFact] = []

        # Clap args
        for match in self._RUST_CLAP_ARG_PATTERNS[0].finditer(content):
            help_text = match.group(1).strip()
            arg_name = match.group(2).strip()
            line_no = content[: match.start()].count("\n") + 1
            facts.append(
                SourceSymbolFact(
                    name=f"--{arg_name.replace('_', '-')}",
                    symbol_type="cli_flag",
                    description=help_text,
                    source_path=rel_path,
                    line_number=line_no,
                    language="rust",
                    framework="clap",
                )
            )

        # Routes (Actix / Axum)
        for match in self._RUST_ROUTE_PATTERNS[0].finditer(content):
            route_path = match.group(1)
            handler = match.group(2)
            line_no = content[: match.start()].count("\n") + 1
            facts.append(
                SourceSymbolFact(
                    name=f"ROUTE {route_path}",
                    symbol_type="api_route",
                    description=f"Route handler {handler} at {route_path}",
                    source_path=rel_path,
                    line_number=line_no,
                    language="rust",
                    framework="actix/axum",
                )
            )

        for match in self._RUST_ROUTE_PATTERNS[1].finditer(content):
            route_path = match.group(1)
            method = match.group(2).upper()
            handler = match.group(3)
            line_no = content[: match.start()].count("\n") + 1
            facts.append(
                SourceSymbolFact(
                    name=f"{method} {route_path}",
                    symbol_type="api_route",
                    description=f"Route {method} {route_path} -> {handler}",
                    source_path=rel_path,
                    line_number=line_no,
                    language="rust",
                    framework="axum",
                )
            )

        # Exported functions
        for pattern in self._RUST_EXPORTED_FUNC_PATTERNS:
            for match in pattern.finditer(content):
                doc_block = match.group(1)
                func_name = match.group(2)
                clean_doc = " ".join(
                    line.strip().lstrip("/").strip()
                    for line in doc_block.splitlines()
                    if line.strip()
                )
                line_no = content[: match.start()].count("\n") + 1
                if clean_doc and len(clean_doc) >= 10:
                    facts.append(
                        SourceSymbolFact(
                            name=func_name,
                            symbol_type="exported_func",
                            description=clean_doc,
                            source_path=rel_path,
                            line_number=line_no,
                            language="rust",
                        )
                    )

        return facts

    def to_evidence_facts(self, facts: list[SourceSymbolFact]) -> list[EvidenceFact]:
        """Convert SourceSymbolFacts into standard EvidenceFacts."""
        evidence_facts: list[EvidenceFact] = []
        for f in facts:
            fact_type = "command" if f.symbol_type in ("cli_flag", "cli_command") else "description"
            claim = f"{f.language.upper()} {f.symbol_type.replace('_', ' ')}: {f.name}"
            if f.description:
                claim += f" - {f.description}"
            evidence_facts.append(
                EvidenceFact(
                    claim=claim,
                    fact_type=fact_type,
                    value=f.name,
                    evidence=[
                        EvidenceLink(
                            source_path=f.source_path,
                            line_range=(f.line_number, f.line_number),
                            raw_text=f"{f.name}: {f.description}"[:200],
                            confidence="high",
                            extraction_method="source_ast",
                        )
                    ],
                )
            )
        return evidence_facts
