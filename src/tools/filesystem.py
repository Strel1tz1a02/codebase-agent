from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.core.paths import resolve_repo_path

MAX_LINES_PER_READ = 500
MAX_CHARS_PER_READ = 50000


class ReadFileInput(BaseModel):
    """read_file 参数：repo_path 必填，其余可选。"""

    repo_path: str = Field(default="", description="Repository root path.")
    path: str = Field(default="", description="Relative file path inside the repository.")
    offset: int = Field(default=1, description="Start line number (1-based). Default 1.")
    limit: int = Field(default=0, description="Maximum lines to read. 0 means read to end.")


def read_file(repo_path: str, path: str, offset: int = 1, limit: int = 0) -> dict[str, object]:
    """
    输入：
        repo_path：代码仓库根目录路径。
        path：仓库内相对文件路径。
        offset：起始行号（1-based），默认第 1 行。
        limit：最多读取行数，0 表示读到底。
    输出：
        dict：包含 path、start_line、end_line、total_lines、content、truncated。
    作用：
        按行号范围读取仓库内 UTF-8 文本文件。默认全量读完，单次硬上限 500 行或 50000 字符。
    """
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
    description="Read lines from a UTF-8 text file inside a repository. Supports offset and limit for position-based reading.",
    args_schema=ReadFileInput,
)

READ_FILE_DESCRIPTION = (
    "read_file: 读取指定文件内容，适合在总览结构后深入查看源码\n"
    "  repo_path: 必填，仓库根目录路径\n"
    "  path: 必填，仓库内相对文件路径\n"
    "  offset: 起始行号（1-based），默认1\n"
    "  limit: 读取行数，0=读到底。硬上限500行/50000字符，超出返回 truncated:true"
)
