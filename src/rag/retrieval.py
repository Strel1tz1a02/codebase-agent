from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from src.core.config import AppConfig
from src.rag.indexing import build_project_index
from src.rag.retrievers import build_retriever
from src.rag.schemas import RagHit, RagIndex


def retrieve_from_index(
    index: RagIndex,
    question: str,
    top_k: int = 5,
) -> list[RagHit]:
    """
    输入：
        index：已构建完成的项目级 RAG 索引。
        question：用户问题文本。
        top_k：本次召回返回的最大命中数量。
    输出：
        list[RagHit]：标准 RAG 召回结果。
    作用：
        基于已有 RagIndex 执行 query，不读取文件、不切 chunk、不重建 vector store。
    为什么需要这个函数：
        retrieval 层只负责召回；索引构建已经由 indexing 层完成，Graph 只需要调用这个稳定入口。
    """
    if index.document_count <= 0:
        return []

    top_k = max(1, int(top_k))
    retriever = build_retriever(index.vector_store, top_k=top_k)
    documents = retriever.invoke(question)
    return [_document_to_hit(document) for document in documents[:top_k]]


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
        top_k：召回返回数量上限。
        reindex：保留的兼容参数；该薄适配每次都会构建临时项目索引。
    输出：
        list[dict[str, object]]：兼容旧工具链路的命中字典。
    作用：
        作为旧入口的兼容层，先调用 build_project_index，再调用 retrieve_from_index。
    为什么需要这个函数：
        新 Runtime/API/CLI 主路径使用 RagIndex；旧工具和测试仍可通过这个函数使用同一套 RAG 边界。
    """
    top_k = max(0, int(top_k))
    if top_k == 0:
        return []

    project_id = Path(repo_path).name
    index = build_project_index(project_id, repo_path, AppConfig())
    return [hit.to_dict() for hit in retrieve_from_index(index, question, top_k)]


def _document_to_hit(document: Document, score: float = 0.0) -> RagHit:
    """
    输入：
        document：LangChain retriever 返回的 Document。
        score：召回分数；当前 retriever 路径暂无原生分数时使用默认值。
    输出：
        RagHit：标准 RAG 命中对象。
    作用：
        将 LangChain Document 转换为 RAG 领域结果。
    为什么需要这个函数：
        Graph 和 Runtime 不应该直接依赖 LangChain Document 的 metadata 结构，转换逻辑应集中在 retrieval 层。
    """
    return RagHit(
        relative_path=str(document.metadata.get("relative_path", "")),
        start_line=int(document.metadata.get("start_line", 0)),
        end_line=int(document.metadata.get("end_line", 0)),
        content=document.page_content,
        score=float(score),
    )
