from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ReadFileInput(BaseModel):
    repo_path: str = Field(default="", description="Repository root path.")
    path: str = Field(default="", description="Relative file path inside the repository.")
    max_chars: int = Field(default=8000, description="Maximum number of characters to read.")


def _read_file(repo_path: str, path: str, max_chars: int = 8000) -> dict[str, object]:
    """
    输入：
        repo_path：代码仓库根目录路径。
        path：仓库内相对文件路径。
        max_chars：最多读取多少字符。
    输出：
        dict：包含 path、content 和 truncated。
    作用：
        读取仓库内指定 UTF-8 文本文件。
    设计原因：
        代码问答经常需要按路径读取源码，工具层需要提供稳定的文件读取能力。
    """
    repo_path = repo_path.strip()
    relative_path = path.strip()

    if not repo_path:
        raise ValueError("repo_path is required")
    if not relative_path:
        raise ValueError("path is required")

    root = Path(repo_path).resolve()
    target = (root / relative_path).resolve()
    try:
        normalized_relative_path = target.relative_to(root).as_posix()
    except ValueError:
        raise ValueError("path must stay inside repo") from None

    if not target.is_file():
        raise FileNotFoundError(f"file not found: {normalized_relative_path}")

    content = target.read_text(encoding="utf-8")
    limit = max(0, max_chars)
    truncated = len(content) > limit
    if truncated:
        content = content[:limit]

    return {
        "path": normalized_relative_path,
        "content": content,
        "truncated": truncated,
    }


read_file_tool = StructuredTool.from_function(
    func=_read_file,
    name="read_file",
    description="Read a UTF-8 text file from inside a repository.",
    args_schema=ReadFileInput,
)
