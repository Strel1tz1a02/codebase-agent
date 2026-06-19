import pytest

from src.core.errors import PathSafetyError
from src.core.paths import iter_repo_files, resolve_repo_path
from src.rag.code_loader import load_code_files
from src.tools.codebase import repo_summary
from src.tools.toolkit import execute_tool


def test_resolve_repo_path_rejects_escape(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(PathSafetyError):
        resolve_repo_path(str(repo), "../outside.txt")


def test_resolve_repo_path_returns_path_inside_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "src" / "main.py"
    source.parent.mkdir()
    source.write_text("print('hi')", encoding="utf-8")

    resolved = resolve_repo_path(str(repo), "src/main.py")

    assert resolved == source.resolve()


def test_iter_repo_files_skips_files_that_resolve_outside_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    escaped = repo / "escaped.py"
    escaped.write_text("print('inside placeholder')\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("print('secret')\n", encoding="utf-8")

    original_resolve = type(escaped).resolve

    def fake_resolve(self, *args, **kwargs):
        if self == escaped:
            return outside
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(type(escaped), "resolve", fake_resolve)

    files = iter_repo_files(str(repo))

    assert files == []


def test_read_file_tool_reports_path_escape(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    result = execute_tool(
        "read_file",
        {
            "repo_path": str(repo),
            "path": "../outside.txt",
        },
    )

    assert result.ok is False
    assert result.tool_name == "read_file"
    assert "path must stay inside repo" in result.error


def test_code_loader_skips_files_that_resolve_outside_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    escaped = repo / "escaped.py"
    escaped.write_text("print('inside placeholder')\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("print('secret')\n", encoding="utf-8")

    original_resolve = type(escaped).resolve
    original_read_text = type(escaped).read_text

    def fake_resolve(self, *args, **kwargs):
        if self == escaped:
            return outside
        return original_resolve(self, *args, **kwargs)

    def fail_if_escaped_file_is_read(self, *args, **kwargs):
        if self == escaped:
            raise AssertionError("escaped path was read before safety check")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(type(escaped), "resolve", fake_resolve)
    monkeypatch.setattr(type(escaped), "read_text", fail_if_escaped_file_is_read)

    records = load_code_files(str(repo))

    assert all(str(item["relative_path"]) != "escaped.py" for item in records)


def test_repo_summary_does_not_count_files_that_resolve_outside_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    escaped = repo / "escaped.py"
    escaped.write_text("print('inside placeholder')\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("print('secret')\n", encoding="utf-8")

    original_resolve = type(escaped).resolve

    def fake_resolve(self, *args, **kwargs):
        if self == escaped:
            return outside
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(type(escaped), "resolve", fake_resolve)

    summary = repo_summary(str(repo))

    assert summary["file_count"] == 0
    assert summary["file_types"] == {}
