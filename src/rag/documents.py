from __future__ import annotations

import hashlib
from pathlib import Path

from langchain_core.documents import Document


LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".md": "markdown",
    ".json": "json",
    ".txt": "text",
}


def infer_language(relative_path: str) -> str:
    """
    输入：
        relative_path：仓库内相对文件路径。
    输出：
        str：根据扩展名推断出的语言名称。
    作用：
        为 LangChain Document metadata 补充 language 字段。
    设计原因：
        后续检索、回答引用和 metadata filter 都需要知道代码块所属语言。
    """
    suffix = Path(relative_path).suffix.lower()
    return LANGUAGE_BY_SUFFIX.get(suffix, "text")


def build_document(
    project_id: str,
    repo_path: str,
    relative_path: str,
    content: str,
    start_line: int,
    end_line: int,
) -> Document:
    """
    输入：
        project_id：项目标识。
        repo_path：仓库根目录路径。
        relative_path：代码块所在的仓库内相对路径。
        content：代码块文本。
        start_line：代码块起始行号。
        end_line：代码块结束行号。
    输出：
        Document：包含 page_content 和标准 metadata 的 LangChain 文档对象。
    作用：
        把项目自己的代码块数据转换为 LangChain RAG 标准文档。
    设计原因：
        后续 VectorStore、Retriever 和 Graph 节点都可以消费统一 Document 接口。
    """
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return Document(
        page_content=content,
        metadata={
            "project_id": project_id,
            "repo_path": repo_path,
            "relative_path": relative_path,
            "start_line": start_line,
            "end_line": end_line,
            "language": infer_language(relative_path),
            "content_hash": content_hash,
        },
    )
