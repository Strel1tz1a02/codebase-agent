from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.core.paths import resolve_repo_path

MAX_LINES_PER_READ = 500
MAX_CHARS_PER_READ = 50000


class ReadFileInput(BaseModel):
    repo_path: str = Field(default="", description="Repository root path.")
    path: str = Field(default="", description="Relative file path inside the repository.")
    offset: int = Field(default=1, description="Start line number, 1-based.")
    limit: int = Field(default=0, description="Maximum lines to read. 0 means read to the end.")


def read_file(repo_path: str, path: str, offset: int = 1, limit: int = 0) -> dict[str, object]:
    repo_path = repo_path.strip()
    relative_path = path.strip()

    if not repo_path:
        raise ValueError("repo_path is required")
    if not relative_path:
        raise ValueError("path is required")

    target = resolve_repo_path(repo_path, relative_path)
    root = resolve_repo_path(repo_path, ".")
    normalized_relative_path = target.relative_to(root).as_posix()

    if not target.is_file():
        raise FileNotFoundError(f"file not found: {normalized_relative_path}")

    all_lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    total_lines = len(all_lines)

    offset = max(1, offset)
    limit = max(0, limit or 0)

    start_index = offset - 1
    if start_index >= total_lines:
        return {
            "path": normalized_relative_path,
            "start_line": offset,
            "end_line": offset,
            "total_lines": total_lines,
            "content": "",
            "truncated": False,
        }

    end_index = start_index + limit if limit > 0 else total_lines
    end_index = min(end_index, total_lines)

    selected_lines = all_lines[start_index:end_index]
    content = "".join(selected_lines)

    line_count = len(selected_lines)
    char_count = len(content)

    truncated = line_count > MAX_LINES_PER_READ or char_count > MAX_CHARS_PER_READ
    if truncated:
        if line_count > MAX_LINES_PER_READ:
            end_index = start_index + MAX_LINES_PER_READ
        if char_count > MAX_CHARS_PER_READ:
            char_limit = MAX_CHARS_PER_READ
            accumulated = 0
            for i, line in enumerate(selected_lines):
                accumulated += len(line)
                if accumulated > char_limit:
                    end_index = start_index + i
                    break
        selected_lines = all_lines[start_index:end_index]
        content = "".join(selected_lines)

    return {
        "path": normalized_relative_path,
        "start_line": start_index + 1,
        "end_line": end_index,
        "total_lines": total_lines,
        "content": content,
        "truncated": truncated,
    }


read_file_tool = StructuredTool.from_function(
    func=read_file,
    name="read_file",
    description=(
        "Read a UTF-8 text file inside a repository. Use this after locating a specific source file "
        "and when exact code lines are needed. Arguments: repo_path is the repository root; path is a "
        "relative path inside the repository; offset is the 1-based start line; limit is the number of "
        "lines to read, with 0 meaning read to the end. The tool enforces repository path safety and "
        "caps large reads."
    ),
    args_schema=ReadFileInput,
)
