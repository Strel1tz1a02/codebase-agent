from __future__ import annotations

from pathlib import Path

from src.utils.file_io import read_utf8_text_file
from src.utils.ignore import should_ignore_dir, should_ignore_file

SUPPORTED_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
}


def load_code_files(repo_path: str) -> list[dict[str, object]]:
    """
    输入：
        repo_path：仓库根目录路径（字符串）。
    输出：
        file_records -- list[dict[str, object]]：代码文件记录列表。
        每条记录包含 file_path（绝对路径）、relative_path（相对仓库路径）、content（文件文本）。
    作用：
        从仓库中加载可分析的文本代码文件，为后续 chunk 切分提供标准化输入。
    设计原因：
        将“目录遍历 + 忽略规则 + 后缀过滤 + UTF-8 读取”收敛到单一入口，
        让上层 RAG 流程只处理结构化文件记录，不关心底层 IO 细节。
    """
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {root}")

    file_records: list[dict[str, object]] = []

    for current_root, dir_names, file_names in root.walk(top_down=True):
        next_dirs: list[str] = []
        for dir_name in dir_names:
            if should_ignore_dir(dir_name):
                continue
            next_dirs.append(dir_name)
        dir_names[:] = next_dirs

        for file_name in file_names:
            file_path = current_root / file_name
            if should_ignore_file(file_path):
                continue
            if file_path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
                continue

            try:
                content = read_utf8_text_file(file_path)
            except (UnicodeDecodeError, OSError):
                continue

            file_records.append(
                {
                    "file_path": str(file_path.resolve()),
                    "relative_path": str(file_path.resolve().relative_to(root)),
                    "content": content,
                }
            )

    file_records.sort(key=lambda item: str(item["relative_path"]).casefold())
    return file_records
