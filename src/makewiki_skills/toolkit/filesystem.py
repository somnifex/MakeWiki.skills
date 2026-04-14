"""Safe helpers for reading, listing, and writing project files."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from makewiki_skills.toolkit.base import ToolResult

class FilesystemTool:
    """All filesystem I/O goes through this tool."""

    name = "filesystem"

    def read_file(self, path: Path, max_bytes: int = 512_000) -> ToolResult:
        """Read a text file and return its content."""
        try:
            real = Path(path).resolve()
            if not real.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            size = real.stat().st_size
            if size > max_bytes:
                return ToolResult(
                    success=False,
                    error=f"File too large ({size} bytes, max {max_bytes})",
                )
            content = real.read_text(encoding="utf-8", errors="replace")
            return ToolResult(
                success=True,
                data={"content": content, "size_bytes": size, "encoding": "utf-8"},
                source_path=str(real),
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def list_directory(
        self,
        path: Path,
        pattern: str = "**/*",
        exclude: list[str] | None = None,
    ) -> ToolResult:
        """List files matching *pattern*, excluding glob patterns in *exclude*."""
        exclude = exclude or []
        try:
            root = Path(path).resolve()
            if not root.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")
            matches: list[str] = []
            for p in root.glob(pattern):
                rel = str(p.relative_to(root)).replace("\\", "/")
                if any(fnmatch.fnmatch(rel, ex) for ex in exclude):
                    continue
                if p.is_file():
                    matches.append(rel)
            matches.sort()
            return ToolResult(success=True, data={"paths": matches, "total": len(matches)})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def get_tree(
        self,
        path: Path,
        max_depth: int = 4,
        exclude: list[str] | None = None,
    ) -> ToolResult:
        """Return an ASCII tree representation of the directory."""
        exclude = exclude or [".git", "node_modules", "__pycache__", ".venv", "venv"]
        try:
            root = Path(path).resolve()
            if not root.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")
            lines: list[str] = [root.name + "/"]
            self._walk_tree(root, "", max_depth, 0, exclude, lines)
            return ToolResult(success=True, data={"tree": "\n".join(lines)})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def _walk_tree(
        self,
        directory: Path,
        prefix: str,
        max_depth: int,
        current_depth: int,
        exclude: list[str],
        lines: list[str],
    ) -> None:
        if current_depth >= max_depth:
            return
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        entries = [e for e in entries if e.name not in exclude]
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "`-- " if is_last else "|-- "
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{connector}{entry.name}{suffix}")
            if entry.is_dir():
                extension = "    " if is_last else "|   "
                self._walk_tree(
                    entry, prefix + extension, max_depth, current_depth + 1, exclude, lines
                )

    def safe_write(self, path: Path, content: str, overwrite: bool = True) -> ToolResult:
        """Write *content* to *path*, creating parent directories as needed."""
        try:
            target = Path(path).resolve()
            if target.exists() and not overwrite:
                return ToolResult(success=False, error=f"File exists and overwrite=False: {path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(success=True, data={"written_bytes": len(content.encode("utf-8"))})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))

    def exists(self, path: Path) -> bool:
        return Path(path).resolve().exists()

    def is_file(self, path: Path) -> bool:
        return Path(path).resolve().is_file()

    def is_dir(self, path: Path) -> bool:
        return Path(path).resolve().is_dir()

    def execute(self, **kwargs) -> ToolResult:  # noqa: D401
        """Dispatch to a named action; prefer the typed methods above."""
        action = kwargs.pop("action", "read_file")
        method = getattr(self, action, None)
        if method is None:
            return ToolResult(success=False, error=f"Unknown action: {action}")
        return method(**kwargs)
