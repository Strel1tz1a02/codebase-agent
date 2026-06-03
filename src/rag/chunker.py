from __future__ import annotations

import ast
from pathlib import Path

MAX_CHARS_PER_CHUNK = 2000

def _split_span_by_max_chars(
    lines: list[str],
    start_line: int,
    end_line: int,
    max_chars: int,
) -> list[tuple[int, int, str]]:
    """
    输入：
        lines：完整文件按行拆分后的文本列表（保留换行符）。
        start_line：当前切分区间起始行号（1-based）。1-based 指从第 1 行开始计数。
        end_line：当前切分区间结束行号（1-based）。
        max_chars：单个 chunk 允许的最大字符数。
    输出：
        list[tuple[int, int, str]]：切分结果，每项为 (start_line, end_line, content)。
    作用：
        在给定行区间内按字符上限进行二次切分，并保留精确行号边界。
    设计原因：
        先按语义边界得到大块后，仍需要统一的“超长再切分”策略，避免 chunk 过大。
    """
    if max_chars <= 0:
        max_chars = 1

    chunks: list[tuple[int, int, str]] = []
    current_lines: list[str] = []
    current_start = start_line
    current_len = 0

    for line_no in range(start_line, end_line + 1):
        line_text = lines[line_no - 1]
        line_len = len(line_text)

        if current_lines and current_len + line_len > max_chars:
            content = "".join(current_lines)
            if content.strip():
                chunks.append((current_start, line_no - 1, content))
            current_lines = []
            current_start = line_no
            current_len = 0

        current_lines.append(line_text)
        current_len += line_len

    if current_lines:
        content = "".join(current_lines)
        if content.strip():
            chunks.append((current_start, end_line, content))

    return chunks


def _build_python_spans(content: str) -> list[tuple[int, int]]:
    """
    输入：
        content：Python 文件全文文本。
    输出：
        list[tuple[int, int]]：按行号表示的切分区间列表（1-based）。
    作用：
        优先按 Python 顶层 class/def/async def 构建语义切分区间。
    设计原因：
        Python 代码天然有结构边界，按顶层定义切分能提高后续检索与召回可读性。
    """
    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    try:
        tree = ast.parse(content) # ast.parse 会自动处理缩进和语法结构，能准确捕捉 class/function 定义边界。
    except SyntaxError:
        return [(1, len(lines))]

    key_nodes_spans: list[tuple[int, int]] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):# AsyncFunctionDef: 异步函数
            start = getattr(node, "lineno", None) # getattr() 参数二是属性名，第三个参数是默认值，如果 node 没有 lineno 属性则返回 None。
            end = getattr(node, "end_lineno", None)
            if isinstance(start, int) and isinstance(end, int):
                key_nodes_spans.append((start, end))

    if not key_nodes_spans:
        return [(1, len(lines))]

    key_nodes_spans.sort(key=lambda item: item[0])
    spans: list[tuple[int, int]] = []
    cursor = 1 # 用于追踪当前行号位置

    for start, end in key_nodes_spans:
        if cursor < start:
            spans.append((cursor, start - 1)) # ？是否有意义
        spans.append((start, end))
        cursor = end + 1

    if cursor <= len(lines):
        spans.append((cursor, len(lines)))

    return [(start, end) for start, end in spans if start <= end]


def chunk_code_file(file_record: dict[str, object], max_chars: int = MAX_CHARS_PER_CHUNK) -> list[dict[str, object]]:
    """
    输入：
        file_record：单文件记录，要求包含 file_path、relative_path、content。
        max_chars：单个 chunk 的字符上限。
    输出：
        list[dict[str, object]]：该文件的 chunk 列表。
        每个 chunk 包含 id、file_path、relative_path、start_line、end_line、content。
    作用：
        将单个文件切分为稳定、有行号元信息的 chunk。
    设计原因：
        统一“Python 语义优先 + 超长再切分 + 非 Python 行累积切分”的单文件策略，
        为后续向量化和检索提供可复现的最小数据单元。
    """
    file_path = str(file_record.get("file_path", ""))
    relative_path = str(file_record.get("relative_path", ""))
    content = str(file_record.get("content", ""))

    if not content:
        return []

    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    suffix = Path(relative_path).suffix.lower()
    # spans 用于确定初始切分边界，优先按 Python 语义边界切分，其他文本文件则默认全文件一个区间。
    if suffix == ".py":
        spans = _build_python_spans(content) 
    else:
        spans = [(1, len(lines))]

    raw_chunks: list[tuple[int, int, str]] = [] # tuple 记录行号区间和文本内容，后续再构建带 id 的 chunk 记录。
    for start_line, end_line in spans:
        raw_chunks.extend(_split_span_by_max_chars(lines, start_line, end_line, max_chars))

    chunks: list[dict[str, object]] = []
    for start_line, end_line, chunk_content in raw_chunks:
        chunk_id = f"{relative_path}:{start_line}:{end_line}"
        chunks.append(
            {
                "id": chunk_id,
                "file_path": file_path,
                "relative_path": relative_path,
                "start_line": start_line,
                "end_line": end_line,
                "content": chunk_content,
            }
        )

    return chunks


def chunk_code_files(file_records: list[dict[str, object]], max_chars: int = MAX_CHARS_PER_CHUNK) -> list[dict[str, object]]:
    """
    输入：
        file_records：多文件记录列表。
        max_chars：单个 chunk 的字符上限。
    输出：
        list[dict[str, object]]：所有文件切分后的 chunk 列表。
    作用：
        按文件顺序批量切分，并汇总成统一 chunk 序列。
    设计原因：
        提供多文件批处理入口，让 CLI 与后续 RAG 流程使用一致的切分 API。
    """
    all_chunks: list[dict[str, object]] = []
    for file_record in file_records:
        all_chunks.extend(chunk_code_file(file_record, max_chars=max_chars))
    return all_chunks
