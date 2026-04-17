"""Track config access in Python source using AST, with grep fallback."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from pydantic import BaseModel

from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


class ConfigAccess(BaseModel):
    """A single config access observation from source code."""

    key_path: str
    source_path: str
    line_number: int
    raw_text: str
    extraction_method: str
    confidence: str


class ConfigAccessTracker:
    """Extract config access facts from Python code."""

    def extract_from_file(self, path: Path) -> list[ConfigAccess]:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except (OSError, SyntaxError):
            return []

        visitor = _ConfigAccessVisitor(source, str(path))
        visitor.visit(tree)
        return self._dedupe(visitor.results)

    def grep_fallback_from_file(self, path: Path) -> list[ConfigAccess]:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []

        results: list[ConfigAccess] = []
        patterns = [
            re.compile(r"""config\[['"]([A-Za-z_][A-Za-z0-9_.-]*)['"]\]"""),
            re.compile(r"""config\.([A-Za-z_][A-Za-z0-9_.-]*)"""),
        ]
        for line_number, line in enumerate(lines, 1):
            matched = False
            for pattern in patterns:
                for match in pattern.finditer(line):
                    matched = True
                    results.append(
                        ConfigAccess(
                            key_path=match.group(1),
                            source_path=str(path),
                            line_number=line_number,
                            raw_text=line.strip(),
                            extraction_method="grep_fallback",
                            confidence="low",
                        )
                    )
            if not matched and "config[" in line:
                results.append(
                    ConfigAccess(
                        key_path="<dynamic>",
                        source_path=str(path),
                        line_number=line_number,
                        raw_text=line.strip(),
                        extraction_method="grep_fallback",
                        confidence="low",
                    )
                )
        return self._dedupe(results)

    def to_evidence_facts(self, accesses: list[ConfigAccess], source_root: Path) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []
        for access in self._dedupe(accesses):
            rel_path = str(Path(access.source_path).resolve().relative_to(source_root)).replace(
                "\\", "/"
            )
            facts.append(
                EvidenceFact(
                    claim=f"Config access: {access.key_path}",
                    fact_type="config_access",
                    value=access.key_path,
                    evidence=[
                        EvidenceLink(
                            source_path=rel_path,
                            line_range=(access.line_number, access.line_number),
                            raw_text=access.raw_text,
                            confidence=access.confidence,  # type: ignore[arg-type]
                            extraction_method=access.extraction_method,
                        )
                    ],
                )
            )
        return facts

    @staticmethod
    def _dedupe(accesses: list[ConfigAccess]) -> list[ConfigAccess]:
        deduped: dict[tuple[str, str, int, str], ConfigAccess] = {}
        for access in accesses:
            key = (access.key_path, access.source_path, access.line_number, access.confidence)
            deduped.setdefault(key, access)

        by_location: dict[tuple[str, int, str], list[ConfigAccess]] = {}
        for access in deduped.values():
            loc_key = (access.source_path, access.line_number, access.confidence)
            by_location.setdefault(loc_key, []).append(access)

        filtered: list[ConfigAccess] = []
        for location_accesses in by_location.values():
            location_accesses.sort(key=lambda item: len(item.key_path), reverse=True)
            kept: list[ConfigAccess] = []
            for access in location_accesses:
                if any(existing.key_path.startswith(f"{access.key_path}.") for existing in kept):
                    continue
                kept.append(access)
            filtered.extend(kept)

        return filtered


class _ConfigAccessVisitor(ast.NodeVisitor):
    def __init__(self, source: str, source_path: str) -> None:
        self._source = source
        self._source_path = source_path
        self.results: list[ConfigAccess] = []
        self._aliases: dict[str, list[str]] = {"config": []}

    def visit_Assign(self, node: ast.Assign) -> None:
        value_path = self._extract_path(node.value)
        if value_path is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._aliases[target.id] = value_path
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and isinstance(node.target, ast.Name):
            value_path = self._extract_path(node.value)
            if value_path is not None:
                self._aliases[node.target.id] = value_path
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        path = self._extract_path(node)
        if path:
            self._record(node, path)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        path = self._extract_path(node)
        if path:
            self._record(node, path)
        self.generic_visit(node)

    def _extract_path(self, node: ast.AST) -> list[str] | None:
        if isinstance(node, ast.Name):
            return list(self._aliases.get(node.id, [])) if node.id in self._aliases else None

        if isinstance(node, ast.Attribute):
            base = self._extract_path(node.value)
            if base is None:
                return None
            return [*base, node.attr]

        if isinstance(node, ast.Subscript):
            base = self._extract_path(node.value)
            if base is None:
                return None
            literal = self._literal_subscript(node.slice)
            if literal is None:
                return None
            return [*base, literal]

        return None

    @staticmethod
    def _literal_subscript(slice_node: ast.AST) -> str | None:
        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            return slice_node.value
        return None

    def _record(self, node: ast.AST, path: list[str]) -> None:
        if not path:
            return
        raw_text = ast.get_source_segment(self._source, node) or ""
        self.results.append(
            ConfigAccess(
                key_path=".".join(path),
                source_path=self._source_path,
                line_number=getattr(node, "lineno", 1),
                raw_text=raw_text,
                extraction_method="python_ast",
                confidence="high",
            )
        )
