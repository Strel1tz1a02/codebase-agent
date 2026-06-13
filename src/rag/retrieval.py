from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from src.core.config import AppConfig
from src.models.embeddings import build_embeddings
from src.rag.chunker import chunk_code_files
from src.rag.code_loader import load_code_files
from src.rag.documents import build_document
from src.rag.indexing import index_documents
from src.rag.retrievers import build_retriever
from src.rag.vectorstores import build_local_vector_store


def _chunk_to_document(project_id: str, repo_path: str, chunk: dict[str, object]) -> Document:
    """
    输入：
        project_id：项目标识。
        repo_path：仓库根目录路径。
        chunk：chunker 产出的代码块字典。
    输出：
        Document：LangChain 标准文档对象。
    作用：
        把代码块数据桥接到 LangChain Document 层。
    设计原因：
        迁移期间保留已有 chunker，同时让检索主路径使用标准 Document/VectorStore/Retriever。
    """
    return build_document(
        project_id=project_id,
        repo_path=repo_path,
        relative_path=str(chunk.get("relative_path", "")),
        content=str(chunk.get("content", "")),
        start_line=int(chunk.get("start_line", 0)),
        end_line=int(chunk.get("end_line", 0)),
    )


def _document_to_result(document: Document, score: float = 0.0) -> dict[str, object]:
    """
    输入：
        document：Retriever 返回的 LangChain Document。
        score：检索分数，当前 retriever 路径暂无原生分数时使用默认值。
    输出：
        dict：兼容 retrieve_relevant_chunks 返回格式的命中字典。
    作用：
        把新 RAG 文档结果转换为工具层可消费的结构。
    设计原因：
        阶段 3 只替换 RAG 内部实现，不打散 CLI、工具和 Agent 的外部契约。
    """
    return {
        "relative_path": str(document.metadata.get("relative_path", "")),
        "start_line": int(document.metadata.get("start_line", 0)),
        "end_line": int(document.metadata.get("end_line", 0)),
        "content": document.page_content,
        "score": float(score),
    }


def retrieve_relevant_chunks(
    question: str,
    repo_path: str,
    top_k: int = 5,
    reindex: bool = False,
) -> list[dict[str, object]]:
    """
    输入：
        question：用户问题文本。
        repo_path：仓库根目录路径。
        top_k：检索返回数量上限。
        reindex：保留的兼容参数；本地内存 VectorStore 每次按当前文件构建。
    输出：
        list[dict[str, object]]：命中 chunks，包含路径、行号、内容和 score。
    作用：
        串联 code loader -> chunker -> Document -> VectorStore -> Retriever -> top-k 检索流程。
    设计原因：
        对外保持原有函数契约，同时主路径迁移到 LangChain 标准 RAG 组件。
    """
    top_k = max(0, int(top_k))
    if top_k == 0:
        return []

    file_records = load_code_files(repo_path)
    chunks = chunk_code_files(file_records)
    if not chunks:
        return []

    project_id = Path(repo_path).name
    documents = [_chunk_to_document(project_id, repo_path, chunk) for chunk in chunks]
    embeddings = build_embeddings(AppConfig().embeddings)
    vector_store = build_local_vector_store(embeddings)
    index_documents(vector_store, documents)

    retriever = build_retriever(vector_store, top_k=top_k)
    hits = retriever.invoke(question)
    return [_document_to_result(document) for document in hits]
