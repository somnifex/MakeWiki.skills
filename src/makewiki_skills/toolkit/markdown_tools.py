"""Validate Markdown structure and extract structured facts from it."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from makewiki_skills.toolkit.base import ToolResult


class Heading(BaseModel):
    level: int
    text: str
    line: int


class CodeBlock(BaseModel):
    language: str | None = None
    content: str
    start_line: int


class MarkdownIssue(BaseModel):
    line: int
    issue_type: str  # "heading_skip" | "broken_link" | "missing_h1" | "empty_page"
    message: str
    severity: str = "warning"  # "error" | "warning"


class FactSet(BaseModel):
    """Structured facts extracted from a rendered Markdown document."""

    language_code: str = ""
    document_name: str = ""
    commands: list[str] = Field(default_factory=list)
    config_keys: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)
    version_strings: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    section_names: list[str] = Field(default_factory=list)


_URI_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

# Path-structure shape: at least one interior segment with a plausible
# repo-path tail (an extension or a multi-segment chain). A bare leading
# slash is NOT path semantics — HTTP routes (`/v1/chat/completions`) and
# anchor-like fragments share that shape with real absolute paths, so they
# must satisfy stricter evidence of file-ness to enter authoritative
# file_paths (L1 existence judges the rest mechanically on disk).
_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")
_SEGMENT_RE = re.compile(r"[\w._-]+")


def _looks_like_repo_path(candidate: str) -> bool:
    """Mechanical gate over backtick path candidates.

    A candidate enters ``file_paths`` only when it carries enough
    repository-relative path semantics. Anything that is primarily a URI,
    an anchor, or an HTTP-style route (root-relative chain without a file
    extension or a leading ``./``/``../`` marker) is excluded. This is a
    shape test, never a project-specific keyword test.
    """
    if not candidate:
        return False
    # Explicit URI scheme (https:, mailto:, file:, ...) -> never a repo path.
    if _URI_SCHEME_RE.match(candidate):
        return False
    # Markdown anchor / fragment.
    if candidate.startswith("#"):
        return False
    # Trailing or leading separator-only junk; must not end with a slash.
    if candidate.endswith("/"):
        return False
    # Query or fragment parts cannot appear inside a plain repo path.
    if "?" in candidate or "#" in candidate:
        return False

    is_doc_relative = candidate.startswith("./") or candidate.startswith("../")
    segments = [s for s in candidate.split("/") if s]

    # Relative forms (./x, ../x) are explicit repo-relative path semantics.
    if is_doc_relative:
        # Must have at least one non-dot segment.
        return any(s not in (".", "..") for s in segments)

    # Root-relative form (/x or plain): only accepted when the tail is a
    # plausibly-named FILE (carries an extension) with at least one interior
    # directory segment, or when it is a multi-segment chain ending in a file.
    # Bare `/name` (single segment, no extension) and extension-less chains
    # (`/v1/chat/completions`) are route-shaped, not path-shaped.
    if len(segments) < 2:
        return False
    if not _EXT_RE.search(segments[-1]):
        return False
    # Every segment must be a plausible path token (no spaces; regex above
    # already constrains the alphabet, this re-checks emptiness).
    return all(_SEGMENT_RE.fullmatch(s) for s in segments)


class MarkdownTool:
    """Validate and extract structured data from Markdown content."""

    name = "markdown"

    def extract_headings(self, content: str) -> list[Heading]:
        headings: list[Heading] = []
        for i, line in enumerate(content.splitlines(), 1):
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                headings.append(
                    Heading(level=len(match.group(1)), text=match.group(2).strip(), line=i)
                )
        return headings

    def validate_headings(self, content: str) -> ToolResult:
        headings = self.extract_headings(content)
        issues: list[MarkdownIssue] = []

        if not headings:
            issues.append(
                MarkdownIssue(
                    line=1, issue_type="missing_h1", message="No headings found", severity="error"
                )
            )
        elif headings[0].level != 1:
            issues.append(
                MarkdownIssue(
                    line=headings[0].line,
                    issue_type="missing_h1",
                    message="First heading should be H1",
                    severity="error",
                )
            )

        h1_count = sum(1 for h in headings if h.level == 1)
        if h1_count > 1:
            issues.append(
                MarkdownIssue(
                    line=1,
                    issue_type="heading_skip",
                    message=f"Multiple H1 headings found ({h1_count})",
                    severity="warning",
                )
            )

        for i in range(1, len(headings)):
            if headings[i].level > headings[i - 1].level + 1:
                issues.append(
                    MarkdownIssue(
                        line=headings[i].line,
                        issue_type="heading_skip",
                        message=f"Heading level jumped from H{headings[i - 1].level} to H{headings[i].level}",
                        severity="warning",
                    )
                )

        return ToolResult(
            success=True,
            data={"issues": [i.model_dump() for i in issues], "valid": len(issues) == 0},
        )

    def validate_links(self, content: str, base_path: Path) -> ToolResult:
        issues: list[MarkdownIssue] = []
        link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
        for i, line in enumerate(content.splitlines(), 1):
            for match in link_pattern.finditer(line):
                target = match.group(2)
                if target.startswith("http://") or target.startswith("https://"):
                    continue  # skip external
                if target.startswith("#"):
                    continue  # skip anchor
                resolved = (Path(base_path).parent / target).resolve()
                if not resolved.exists():
                    issues.append(
                        MarkdownIssue(
                            line=i,
                            issue_type="broken_link",
                            message=f"Broken internal link: {target}",
                            severity="error",
                        )
                    )
        return ToolResult(
            success=True,
            data={"issues": [i.model_dump() for i in issues], "valid": len(issues) == 0},
        )

    def extract_code_blocks(self, content: str) -> list[CodeBlock]:
        blocks: list[CodeBlock] = []
        pattern = re.compile(r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL)
        for match in pattern.finditer(content):
            lang = match.group(1) or None
            start_line = content[: match.start()].count("\n") + 1
            blocks.append(CodeBlock(language=lang, content=match.group(2), start_line=start_line))
        return blocks

    def extract_facts(
        self, content: str, language_code: str = "", document_name: str = ""
    ) -> FactSet:
        facts = FactSet(language_code=language_code, document_name=document_name)

        headings = self.extract_headings(content)
        facts.section_names = [h.text for h in headings]

        blocks = self.extract_code_blocks(content)
        for block in blocks:
            if block.language in ("bash", "sh", "shell", "console", None):
                for line in block.content.strip().splitlines():
                    line = line.strip()
                    if line.startswith("$"):
                        line = line[1:].strip()
                    if line and not line.startswith("#") and not line.startswith("//"):
                        facts.commands.append(line)

        config_pattern = re.compile(r"`([A-Z_][A-Z0-9_]*)`")
        facts.config_keys = list(set(config_pattern.findall(content)))

        dotted_pattern = re.compile(r"`([\w]+\.[\w.]+)`")
        facts.config_keys.extend(set(dotted_pattern.findall(content)))
        facts.config_keys = sorted(set(facts.config_keys))

        path_pattern = re.compile(r"`((?:\./|\.\./|/)[\w./_-]+)`")
        facts.file_paths = sorted(
            {p for p in path_pattern.findall(content) if _looks_like_repo_path(p)}
        )

        version_pattern = re.compile(r"\b(\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9.+-]*))\b")
        facts.version_strings = sorted(set(version_pattern.findall(content)))

        url_pattern = re.compile(r"https?://[^\s\)\"'>]+")
        facts.urls = sorted(set(url_pattern.findall(content)))

        return facts

    def check_empty(self, content: str) -> bool:
        """Return True if the page has no meaningful content."""
        stripped = re.sub(r"^#.*$", "", content, flags=re.MULTILINE).strip()
        return len(stripped) < 10

    def execute(self, **kwargs: Any) -> ToolResult:
        content = kwargs.get("content", "")
        return self.validate_headings(content)
