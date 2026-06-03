from __future__ import annotations

from pathlib import Path


def read_utf8_text_file(file_path: str | Path, max_chars: int | None = None) -> str:
    """
    输入：
        file_path：要读取的文件路径（str 或 Path）。
        max_chars：最多读取的字符数；为 None 时读取全文。
    输出：
        str：读取到的 UTF-8 文本内容。
    作用：
        提供统一的 UTF-8 文本读取入口，供不同模块复用。
    设计原因：
        把底层文件读取逻辑集中在一个函数里，避免业务模块重复实现读取细节。
    """
    path = Path(file_path)
    if max_chars is None:
        return path.read_text(encoding="utf-8")

    limit = max(0, int(max_chars))
    with path.open("r", encoding="utf-8") as file_obj:
        return file_obj.read(limit)
