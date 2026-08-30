"""Output validator - validates generated makewiki output."""

from __future__ import annotations

from pathlib import Path

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
    """Validate the generated makewiki/ directory.

    This is a purely mechanical (L0) validator: it checks markdown structure
    and links. Prose-level quality (banned descriptors, AI clichés, forbidden
    developer-facing headings) is cognitive judgment and belongs to the LLM
    writer plane, not the deterministic Python plane.
    """

    def __init__(self) -> None:
        self._md = MarkdownTool()

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
            present = [
                lang for lang in expected_languages if base in pages_by_lang.get(lang, set())
            ]
            missing = [lang for lang in expected_languages if lang not in present]
            if missing:
                issues.append(f"Page '{base}' missing for languages: {missing}")

        return issues
