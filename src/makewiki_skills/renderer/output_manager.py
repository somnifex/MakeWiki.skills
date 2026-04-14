"""Output manager - writes generated documents to the makewiki/ directory."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.toolkit.filesystem import FilesystemTool


class OutputManager:
    """Write final documents to the output directory."""

    def __init__(self, output_dir: Path, overwrite: bool = True) -> None:
        self._output_dir = Path(output_dir)
        self._overwrite = overwrite
        self._fs = FilesystemTool()

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
        return written

    def write_index(
        self,
        documents: dict[str, list[GeneratedDocument]],
        default_language: str = "en",
    ) -> Path | None:
        del default_language

        lines = ["# MakeWiki Documentation\n\n"]

        for lang in sorted(documents.keys()):
            docs = documents[lang]
            if not docs:
                continue
            lines.append(f"## {lang}\n\n")
            for doc in sorted(docs, key=lambda item: item.base_name):
                lines.append(f"- [{doc.base_name}]({doc.filename})\n")
            lines.append("\n")

        content = "".join(lines)
        target = self._output_dir / "index.md"
        result = self._fs.safe_write(target, content, overwrite=self._overwrite)
        return target if result.success else None
