"""Extract comments adjacent to config definitions in YAML, TOML, .env, and INI files."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


class ConfigComment(BaseModel):
    """A comment associated with a config key."""

    key: str
    comment_text: str
    source_path: str
    line_number: int
    comment_type: str = "preceding"  # "preceding" | "inline" | "section_header"


class CommentExtractor:
    """Extract comments adjacent to config definitions.

    Standard config-file parsers (PyYAML, tomllib, json) discard comments.
    This extractor works at the raw-text level to preserve them.
    """

    def extract_comments(self, path: Path) -> list[ConfigComment]:
        suffix = path.suffix.lower()
        name = path.name.lower()

        if name.startswith(".env"):
            return self.extract_env_comments(path)
        if suffix in (".yaml", ".yml"):
            return self.extract_yaml_comments(path)
        if suffix == ".toml":
            return self.extract_toml_comments(path)
        if suffix in (".ini", ".cfg"):
            return self.extract_ini_comments(path)
        return []

    def extract_env_comments(self, path: Path) -> list[ConfigComment]:
        """Extract comments from .env / .env.example files.

        Pattern: one or more ``# comment`` lines immediately preceding a
        ``KEY=value`` line are associated with that key.
        """
        results: list[ConfigComment] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return results

        rel_path = str(path)
        pending_comments: list[str] = []
        pending_start_line = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                pending_comments.clear()
                continue

            if stripped.startswith("#"):
                if not pending_comments:
                    pending_start_line = i
                pending_comments.append(stripped.lstrip("#").strip())
                continue

            env_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
            if env_match and pending_comments:
                results.append(
                    ConfigComment(
                        key=env_match.group(1),
                        comment_text=" ".join(pending_comments),
                        source_path=rel_path,
                        line_number=pending_start_line,
                        comment_type="preceding",
                    )
                )

            if env_match:
                inline_match = re.search(r"\s+#\s*(.+)$", stripped)
                if inline_match:
                    results.append(
                        ConfigComment(
                            key=env_match.group(1),
                            comment_text=inline_match.group(1).strip(),
                            source_path=rel_path,
                            line_number=i,
                            comment_type="inline",
                        )
                    )

            pending_comments.clear()

        return results

    def extract_yaml_comments(self, path: Path) -> list[ConfigComment]:
        """Extract comments from YAML files.

        Pattern: ``# comment`` lines immediately preceding a ``key:`` line.
        """
        results: list[ConfigComment] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return results

        rel_path = str(path)
        pending_comments: list[str] = []
        pending_start_line = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                pending_comments.clear()
                continue

            if stripped.startswith("#"):
                if not pending_comments:
                    pending_start_line = i
                pending_comments.append(stripped.lstrip("#").strip())
                continue

            key_match = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_.-]*)\s*:", stripped)
            if key_match and pending_comments:
                results.append(
                    ConfigComment(
                        key=key_match.group(2),
                        comment_text=" ".join(pending_comments),
                        source_path=rel_path,
                        line_number=pending_start_line,
                        comment_type="preceding",
                    )
                )

            if key_match:
                inline_match = re.search(r"\s+#\s*(.+)$", line)
                if inline_match:
                    results.append(
                        ConfigComment(
                            key=key_match.group(2),
                            comment_text=inline_match.group(1).strip(),
                            source_path=rel_path,
                            line_number=i,
                            comment_type="inline",
                        )
                    )

            pending_comments.clear()

        return results

    def extract_toml_comments(self, path: Path) -> list[ConfigComment]:
        """Extract comments from TOML files."""
        results: list[ConfigComment] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return results

        rel_path = str(path)
        pending_comments: list[str] = []
        pending_start_line = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                pending_comments.clear()
                continue

            if stripped.startswith("#"):
                if not pending_comments:
                    pending_start_line = i
                pending_comments.append(stripped.lstrip("#").strip())
                continue

            key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*=", stripped)
            if key_match and pending_comments:
                results.append(
                    ConfigComment(
                        key=key_match.group(1),
                        comment_text=" ".join(pending_comments),
                        source_path=rel_path,
                        line_number=pending_start_line,
                        comment_type="preceding",
                    )
                )

            if key_match:
                inline_match = re.search(r"\s+#\s*(.+)$", line)
                if inline_match:
                    results.append(
                        ConfigComment(
                            key=key_match.group(1),
                            comment_text=inline_match.group(1).strip(),
                            source_path=rel_path,
                            line_number=i,
                            comment_type="inline",
                        )
                    )

            pending_comments.clear()

        return results

    def extract_ini_comments(self, path: Path) -> list[ConfigComment]:
        """Extract comments from INI/CFG files."""
        results: list[ConfigComment] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return results

        rel_path = str(path)
        pending_comments: list[str] = []
        pending_start_line = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped:
                pending_comments.clear()
                continue

            if stripped.startswith(("#", ";")):
                if not pending_comments:
                    pending_start_line = i
                pending_comments.append(stripped.lstrip("#;").strip())
                continue

            key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*[=:]", stripped)
            if key_match and pending_comments:
                results.append(
                    ConfigComment(
                        key=key_match.group(1),
                        comment_text=" ".join(pending_comments),
                        source_path=rel_path,
                        line_number=pending_start_line,
                        comment_type="preceding",
                    )
                )

            pending_comments.clear()

        return results

    def to_evidence_facts(self, comments: list[ConfigComment]) -> list[EvidenceFact]:
        facts: list[EvidenceFact] = []
        for comment in comments:
            facts.append(
                EvidenceFact(
                    claim=f"Config comment for {comment.key}: {comment.comment_text[:80]}",
                    fact_type="config_comment",
                    value=comment.key,
                    evidence=[
                        EvidenceLink(
                            source_path=comment.source_path,
                            line_range=(comment.line_number, comment.line_number),
                            raw_text=comment.comment_text,
                            confidence="medium",
                            extraction_method="comment_extraction",
                        )
                    ],
                )
            )
        return facts
