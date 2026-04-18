"""Output validator - validates generated makewiki output."""

from __future__ import annotations

import re
from pathlib import Path

from makewiki_skills.config import DocumentationPolicyConfig
from makewiki_skills.toolkit.markdown_tools import MarkdownIssue, MarkdownTool


class ValidationReport:
    """Holds all issues found during validation."""

    def __init__(self) -> None:
        self.issues: list[MarkdownIssue] = []
        self.files_checked: int = 0
        self.files_with_issues: int = 0

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def summary(self) -> str:
        errors = sum(1 for issue in self.issues if issue.severity == "error")
        warnings = sum(1 for issue in self.issues if issue.severity == "warning")
        return f"Checked {self.files_checked} files: {errors} errors, {warnings} warnings"


class OutputValidator:
    """Validate the generated makewiki/ directory."""

    def __init__(self, documentation_policy: DocumentationPolicyConfig | None = None) -> None:
        self._md = MarkdownTool()
        self._policy = documentation_policy or DocumentationPolicyConfig()

    def validate(self, output_dir: Path) -> ValidationReport:
        report = ValidationReport()
        output = Path(output_dir)
        if not output.is_dir():
            report.issues.append(
                MarkdownIssue(
                    line=0,
                    issue_type="missing_dir",
                    message=f"Output directory does not exist: {output}",
                    severity="error",
                )
            )
            return report

        md_files = list(output.rglob("*.md"))
        report.files_checked = len(md_files)

        for md_file in md_files:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            file_has_issues = False

            if self._md.check_empty(content):
                report.issues.append(
                    MarkdownIssue(
                        line=0,
                        issue_type="empty_page",
                        message=f"Empty or near-empty page: {md_file.name}",
                        severity="warning",
                    )
                )
                file_has_issues = True

            headings = self._md.validate_headings(content)
            if headings.success and headings.data:
                for issue_data in headings.data["issues"]:
                    report.issues.append(MarkdownIssue(**issue_data))
                    file_has_issues = True

            links = self._md.validate_links(content, md_file)
            if links.success and links.data:
                for issue_data in links.data["issues"]:
                    report.issues.append(MarkdownIssue(**issue_data))
                    file_has_issues = True

            policy_issues = self._check_policy(content)
            if policy_issues:
                report.issues.extend(policy_issues)
                file_has_issues = True

            if file_has_issues:
                report.files_with_issues += 1

        return report

    def check_language_alignment(
        self,
        output_dir: Path,
        expected_languages: list[str],
        default_language: str = "en",
    ) -> list[str]:
        output = Path(output_dir)
        issues: list[str] = []
        pages_by_lang: dict[str, set[str]] = {lang: set() for lang in expected_languages}

        for md_file in output.rglob("*.md"):
            if md_file.name == "index.md":
                continue

            name = md_file.name
            rel_dir = md_file.parent.relative_to(output)
            prefix = str(rel_dir).replace("\\", "/")
            if prefix == ".":
                prefix = ""

            matched_lang = default_language
            for lang in expected_languages:
                if lang == default_language:
                    continue
                suffix = f".{lang}"
                if suffix in name:
                    matched_lang = lang
                    name = name.replace(suffix, "")
                    break

            full_base = f"{prefix}/{name}" if prefix else name
            if matched_lang in pages_by_lang:
                pages_by_lang[matched_lang].add(full_base)

        all_bases: set[str] = set()
        for pages in pages_by_lang.values():
            all_bases.update(pages)

        for base in sorted(all_bases):
            present = [lang for lang in expected_languages if base in pages_by_lang.get(lang, set())]
            missing = [lang for lang in expected_languages if lang not in present]
            if missing:
                issues.append(f"Page '{base}' missing for languages: {missing}")

        return issues

    def _check_policy(self, content: str) -> list[MarkdownIssue]:
        issues: list[MarkdownIssue] = []
        issues.extend(self._check_banned_descriptors(content))
        issues.extend(self._check_forbidden_headings(content))
        return issues

    def _check_banned_descriptors(self, content: str) -> list[MarkdownIssue]:
        if not self._policy.forbid_unfounded_praise:
            return []

        stripped = self._strip_code(content)
        issues: list[MarkdownIssue] = []
        for word in self._policy.banned_descriptors:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            match = pattern.search(stripped)
            if not match:
                continue
            issues.append(
                MarkdownIssue(
                    line=self._line_number(stripped, match.start()),
                    issue_type="banned_descriptor",
                    message=f"Found discouraged descriptor without evidence: {word}",
                    severity="warning",
                )
            )
        return issues

    def _check_forbidden_headings(self, content: str) -> list[MarkdownIssue]:
        issues: list[MarkdownIssue] = []
        for heading in self._md.extract_headings(content):
            text = heading.text.lower()
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in _FORBIDDEN_HEADING_PATTERNS):
                issues.append(
                    MarkdownIssue(
                        line=heading.line,
                        issue_type="forbidden_heading",
                        message=f"Developer-facing heading found in user docs: {heading.text}",
                        severity="warning",
                    )
                )
        return issues

    @staticmethod
    def _strip_code(content: str) -> str:
        without_blocks = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
        return re.sub(r"`[^`]+`", "", without_blocks)

    @staticmethod
    def _line_number(content: str, offset: int) -> int:
        return content.count("\n", 0, offset) + 1


_FORBIDDEN_HEADING_PATTERNS = (
    r"\barchitecture\b",
    r"\bproject structure\b",
    r"\bdirectory\b",
    r"\bmodule(?:s)?\b",
    r"\bclass diagram\b",
    r"\bpackage diagram\b",
    r"\bdesign pattern(?:s)?\b",
    r"\bsource code\b",
    "\u67b6\u6784",
    "\u76ee\u5f55",
    "\u6a21\u5757",
    "\u7c7b\u56fe",
    "\u5305\u56fe",
    "\u6e90\u7801",
)
