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
        planned = [
            OutputFilePlan(
                target=self._output_dir / doc.filename,
                relative_path=doc.filename,
                content=doc.content,
            )
            for docs in documents.values()
            for doc in docs
        ]
        planned.append(
            OutputFilePlan(
                target=self._output_dir / "index.md",
                relative_path="index.md",
                content=self.build_index_content(documents, default_language),
            )
        )
        stale_files = self._find_stale_files(planned) if self._delete_stale else []
        return planned, stale_files

    def write_documents(
        self, documents: dict[str, list[GeneratedDocument]]
    ) -> list[Path]:
        written: list[Path] = []
        for _lang, docs in documents.items():
            for doc in docs:
                target = self._output_dir / doc.filename
                result = self._fs.safe_write(target, doc.content, overwrite=self._overwrite)
                if result.success:
                    written.append(target)

        if self._delete_stale and written:
            self._remove_stale_files(written)

        return written

    def _remove_stale_files(self, written: list[Path]) -> None:
        """Delete .md files in the output directory that were not just written."""
        if not self._output_dir.is_dir():
            return
        freshly_written = {path.resolve() for path in written}
        for md_file in self._output_dir.rglob("*.md"):
            if md_file.resolve() not in freshly_written:
                md_file.unlink(missing_ok=True)

    def write_index(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> Path | None:
        content = self.build_index_content(documents, default_language)
        target = self._output_dir / "index.md"
        result = self._fs.safe_write(target, content, overwrite=self._overwrite)
        return target if result.success else None

    def build_index_content(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> str:
        del default_language

        lines = ["# MakeWiki Documentation\n\n"]

        for lang in sorted(documents.keys()):
            docs = documents[lang]
            if not docs:
                continue
            lines.append(f"## {lang}\n\n")

            # Separate top-level docs from sub-pages (e.g. usage/*)
            top_level: list[GeneratedDocument] = []
            by_dir: dict[str, list[GeneratedDocument]] = {}
            for doc in sorted(docs, key=lambda item: item.base_name):
                parts = doc.base_name.split("/", 1)
                if len(parts) == 2:
                    by_dir.setdefault(parts[0], []).append(doc)
                else:
                    top_level.append(doc)

            for doc in top_level:
                lines.append(f"- [{doc.base_name}]({doc.filename})\n")

            for dirname, sub_docs in sorted(by_dir.items()):
                lines.append(f"- **{dirname}/**\n")
                for doc in sub_docs:
                    lines.append(f"  - [{doc.base_name.split('/', 1)[1]}]({doc.filename})\n")

            lines.append("\n")

        return "".join(lines)

    def _find_stale_files(self, planned: list[OutputFilePlan]) -> list[Path]:
        if not self._output_dir.is_dir():
            return []
        freshly_written = {file.target.resolve() for file in planned}
        stale_files: list[Path] = []
        for md_file in self._output_dir.rglob("*.md"):
            if md_file.resolve() not in freshly_written:
                stale_files.append(md_file)
        return stale_files
