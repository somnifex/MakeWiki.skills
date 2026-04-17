"""Output manager - writes generated documents to the makewiki/ directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.toolkit.filesystem import FilesystemTool


@dataclass(frozen=True)
class OutputFilePlan:
    """A single output file that can be materialized by the agent or toolkit."""

    target: Path
    relative_path: str
    content: str


class OutputManager:
    """Write final documents to the output directory."""

    def __init__(
        self,
        output_dir: Path,
        overwrite: bool = True,
        delete_stale_files: bool = False,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._overwrite = overwrite
        self._delete_stale = delete_stale_files
        self._fs = FilesystemTool()

    def plan_output_files(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> tuple[list[OutputFilePlan], list[Path]]:
        """Return the full output file plan plus any stale markdown files."""
        planned = self._build_output_file_plans(documents, default_language)
        stale_files = self._find_stale_files(planned) if self._delete_stale else []
        stale_files.extend(path for path in self._legacy_index_files() if path not in stale_files)
        return planned, stale_files

    def write_documents(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> list[Path]:
        written: list[Path] = []
        for file_plan in self._build_output_file_plans(documents, default_language):
            result = self._fs.safe_write(
                file_plan.target,
                file_plan.content,
                overwrite=self._overwrite,
            )
            if result.success:
                written.append(file_plan.target)

        self._remove_legacy_index_files()

        if self._delete_stale and written:
            self._remove_stale_files(written)

        return written

    def write_index(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> Path | None:
        """Refresh the default README entry page with generated navigation."""
        readme_plan = next(
            (
                plan
                for plan in self._build_output_file_plans(documents, default_language)
                if plan.relative_path == _readme_filename(default_language, default_language)
            ),
            None,
        )
        if readme_plan is None:
            return None

        result = self._fs.safe_write(
            readme_plan.target,
            readme_plan.content,
            overwrite=self._overwrite,
        )
        self._remove_legacy_index_files()
        return readme_plan.target if result.success else None

    def build_index_content(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> str:
        """Backward-compatible helper that now returns README landing-page content."""
        return self._build_synthetic_readme_content(
            documents,
            default_language,
            default_language,
        )

    def _build_output_file_plans(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str,
    ) -> list[OutputFilePlan]:
        planned: list[OutputFilePlan] = []
        for language, docs in documents.items():
            language_start = len(planned)
            sorted_docs = sorted(docs, key=self._document_sort_key)
            readme_seen = False

            for doc in sorted_docs:
                content = doc.content
                if self._is_readme(doc):
                    readme_seen = True
                    content = self._build_readme_content(
                        readme_doc=doc,
                        documents=documents,
                        language=language,
                        default_language=default_language,
                    )
                planned.append(
                    OutputFilePlan(
                        target=self._output_dir / doc.filename,
                        relative_path=doc.filename,
                        content=content,
                    )
                )

            if not readme_seen:
                filename = _readme_filename(language, default_language)
                planned.insert(
                    language_start,
                    OutputFilePlan(
                        target=self._output_dir / filename,
                        relative_path=filename,
                        content=self._build_synthetic_readme_content(
                            documents,
                            language,
                            default_language,
                        ),
                    ),
                )

        return planned

    def _build_readme_content(
        self,
        readme_doc: GeneratedDocument,
        documents: dict[str, list[GeneratedDocument]],
        language: str,
        default_language: str,
    ) -> str:
        navigation = self._build_readme_navigation(documents, language, default_language)
        content = readme_doc.content.rstrip()
        if content:
            return f"{content}\n\n{navigation}"
        return navigation

    def _build_synthetic_readme_content(
        self,
        documents: dict[str, list[GeneratedDocument]],
        language: str,
        default_language: str,
    ) -> str:
        title, _languages_title = _localized_readme_labels(language)
        navigation = self._build_readme_navigation(documents, language, default_language)
        return f"# {title}\n\n{navigation}"

    def _build_readme_navigation(
        self,
        documents: dict[str, list[GeneratedDocument]],
        language: str,
        default_language: str,
    ) -> str:
        index_title, languages_title = _localized_readme_labels(language)
        lines = [f"## {index_title}\n\n"]

        docs = sorted(documents.get(language, []), key=self._document_sort_key)
        top_level: list[GeneratedDocument] = []
        by_dir: dict[str, list[GeneratedDocument]] = {}
        for doc in docs:
            if self._is_readme(doc):
                continue
            parts = doc.base_name.split("/", 1)
            if len(parts) == 2:
                by_dir.setdefault(parts[0], []).append(doc)
            else:
                top_level.append(doc)

        for doc in top_level:
            lines.append(f"- [{doc.base_name}]({doc.filename})\n")

        for dirname, sub_docs in sorted(by_dir.items()):
            lines.append(f"- **{dirname}/**\n")
            for doc in sorted(sub_docs, key=lambda item: item.base_name.lower()):
                lines.append(f"  - [{doc.base_name.split('/', 1)[1]}]({doc.filename})\n")

        readme_links = self._readme_links_by_language(documents, default_language)
        other_languages = [
            (lang_code, filename)
            for lang_code, filename in readme_links
            if lang_code != language
        ]
        if other_languages:
            lines.append(f"\n## {languages_title}\n\n")
            for lang_code, filename in other_languages:
                lines.append(f"- [{lang_code}]({filename})\n")

        return "".join(lines).rstrip() + "\n"

    def _readme_links_by_language(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str,
    ) -> list[tuple[str, str]]:
        links: list[tuple[str, str]] = []
        for language, docs in documents.items():
            readme_doc = next((doc for doc in docs if self._is_readme(doc)), None)
            if readme_doc is not None:
                links.append((language, readme_doc.filename))
            else:
                links.append((language, _readme_filename(language, default_language)))
        return links

    def _remove_stale_files(self, written: list[Path]) -> None:
        """Delete .md files in the output directory that were not just written."""
        if not self._output_dir.is_dir():
            return
        freshly_written = {path.resolve() for path in written}
        for md_file in self._output_dir.rglob("*.md"):
            if md_file.resolve() not in freshly_written:
                md_file.unlink(missing_ok=True)

    def _find_stale_files(self, planned: list[OutputFilePlan]) -> list[Path]:
        if not self._output_dir.is_dir():
            return []
        freshly_written = {file.target.resolve() for file in planned}
        stale_files: list[Path] = []
        for md_file in self._output_dir.rglob("*.md"):
            if md_file.resolve() not in freshly_written:
                stale_files.append(md_file)
        return stale_files

    def _legacy_index_files(self) -> list[Path]:
        legacy_index = self._output_dir / "index.md"
        return [legacy_index] if legacy_index.exists() else []

    def _remove_legacy_index_files(self) -> None:
        for path in self._legacy_index_files():
            path.unlink(missing_ok=True)

    @staticmethod
    def _document_sort_key(doc: GeneratedDocument) -> tuple[int, str]:
        return (0 if OutputManager._is_readme(doc) else 1, doc.base_name.lower())

    @staticmethod
    def _is_readme(doc: GeneratedDocument) -> bool:
        return doc.base_name.lower() == "readme.md"


def _readme_filename(language: str, default_language: str) -> str:
    if language == default_language:
        return "README.md"
    return f"README.{language}.md"


def _localized_readme_labels(language: str) -> tuple[str, str]:
    labels = {
        "de": ("Dokumentationsindex", "Weitere Sprachen"),
        "en": ("Documentation Index", "Other Languages"),
        "fr": ("Index de la documentation", "Autres langues"),
        "ja": ("\u30c9\u30ad\u30e5\u30e1\u30f3\u30c8\u4e00\u89a7", "\u4ed6\u306e\u8a00\u8a9e"),
        "zh-CN": ("\u6587\u6863\u7d22\u5f15", "\u5176\u4ed6\u8bed\u8a00"),
    }
    return labels.get(language, labels["en"])
