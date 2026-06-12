from __future__ import annotations

from pathlib import Path

from src.core.errors import PathSafetyError


def resolve_repo_path(repo_path: str, relative_path: str) -> Path:
    """
    输入：
        repo_path：代码仓库根目录路径。
        relative_path：仓库内相对路径。
    输出：
        Path：解析后的绝对路径。
    作用：
        确保目标路径位于仓库根目录内部。
    设计原因：
        read_file、search_code 等工具会访问本地文件，统一路径安全检查可以避免路径逃逸。
    """
    root = Path(repo_path).resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise PathSafetyError("path must stay inside repo") from None
    return target
