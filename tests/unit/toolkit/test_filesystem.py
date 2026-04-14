"""Tests for FilesystemTool."""

from pathlib import Path

from makewiki_skills.toolkit.filesystem import FilesystemTool


def test_read_file(tmp_path: Path):
    f = tmp_path / "hello.txt"
    f.write_text("Hello, World!", encoding="utf-8")

    tool = FilesystemTool()
    result = tool.read_file(f)
    assert result.success
    assert result.data["content"] == "Hello, World!"
    assert result.data["encoding"] == "utf-8"


def test_read_file_nonexistent(tmp_path: Path):
    tool = FilesystemTool()
    result = tool.read_file(tmp_path / "nope.txt")
    assert not result.success
    assert "Not a file" in result.error


def test_read_file_too_large(tmp_path: Path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 1000, encoding="utf-8")

    tool = FilesystemTool()
    result = tool.read_file(f, max_bytes=100)
    assert not result.success
    assert "too large" in result.error.lower()


def test_list_directory(tmp_path: Path):
    (tmp_path / "a.py").write_text("pass")
    (tmp_path / "b.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("pass")

    tool = FilesystemTool()
    result = tool.list_directory(tmp_path, pattern="**/*.py")
    assert result.success
    assert "a.py" in result.data["paths"]
    assert "sub/c.py" in result.data["paths"]


def test_list_directory_with_exclude(tmp_path: Path):
    (tmp_path / "keep.py").write_text("pass")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x")

    tool = FilesystemTool()
    result = tool.list_directory(tmp_path, pattern="*", exclude=["node_modules/*"])
    assert result.success
    paths = result.data["paths"]
    assert "keep.py" in paths
    assert not any("node_modules" in p for p in paths)


def test_get_tree(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("pass")
    (tmp_path / "README.md").write_text("# Hello")

    tool = FilesystemTool()
    result = tool.get_tree(tmp_path, max_depth=2)
    assert result.success
    tree = result.data["tree"]
    assert "src/" in tree
    assert "main.py" in tree
    assert "README.md" in tree


def test_safe_write(tmp_path: Path):
    target = tmp_path / "out" / "doc.md"
    tool = FilesystemTool()
    result = tool.safe_write(target, "# Hello\n")
    assert result.success
    assert target.read_text(encoding="utf-8") == "# Hello\n"


def test_safe_write_no_overwrite(tmp_path: Path):
    target = tmp_path / "doc.md"
    target.write_text("original")
    tool = FilesystemTool()
    result = tool.safe_write(target, "new content", overwrite=False)
    assert not result.success
    assert target.read_text() == "original"


def test_exists_helpers(tmp_path: Path):
    f = tmp_path / "test.txt"
    f.write_text("x")
    tool = FilesystemTool()
    assert tool.exists(f)
    assert tool.is_file(f)
    assert not tool.is_dir(f)
    assert tool.is_dir(tmp_path)
