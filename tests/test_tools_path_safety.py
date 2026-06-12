import pytest

from src.core.errors import PathSafetyError
from src.core.paths import resolve_repo_path
from src.tools.registry import execute_tool


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
