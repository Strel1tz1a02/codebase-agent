from __future__ import annotations

from collections.abc import Callable, Collection
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


def iter_repo_files(
    repo_path: str,
    *,
    should_ignore_dir: Callable[[str], bool] | None = None,
    should_ignore_file: Callable[[Path], bool] | None = None,
    suffixes: Collection[str] | None = None,
) -> list[Path]:
    '''
        校验 repo 根目录存在且是目录
        遍历文件
        应用 ignore 规则
        应用后缀过滤
        调用 resolve_repo_path 做越界检查
        只返回已经 resolve 且仍在 repo 内的安全路径
    '''
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"path is not a directory: {root}")

    normalized_suffixes = {suffix.lower() for suffix in suffixes} if suffixes is not None else None
    files: list[Path] = []

    for current_root, dir_names, file_names in root.walk(top_down=True):
        if should_ignore_dir is not None:
            dir_names[:] = [dir_name for dir_name in dir_names if not should_ignore_dir(dir_name)]

        for file_name in file_names:
            file_path = current_root / file_name
            if should_ignore_file is not None and should_ignore_file(file_path):
                continue
            if normalized_suffixes is not None and file_path.suffix.lower() not in normalized_suffixes:
                continue

            try:
                relative_path = file_path.relative_to(root).as_posix()
                files.append(resolve_repo_path(str(root), relative_path))
            except (PathSafetyError, ValueError):
                continue

    files.sort(key=lambda path: path.as_posix().casefold())
    return files
