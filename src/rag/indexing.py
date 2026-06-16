from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

from src.core.config import AppConfig
from src.models.embeddings import build_embeddings
from src.rag.chunker import chunk_code_files
from src.rag.code_loader import load_code_files
from src.rag.documents import build_document
from src.rag.schemas import RagIndex
from src.rag.vectorstores import build_local_vector_store


def _index_documents(vector_store: VectorStore, documents: list[Document]) -> list[str]:
    """
    输入：
        vector_store：目标 LangChain VectorStore。
        documents：待写入的 LangChain Document 列表。
    输出：
        list[str]：VectorStore 返回的文档 ID 列表。
    作用：
        把标准 Document 写入向量存储。
    设计原因：
        RAG 标准化需要一个明确的 indexing 边界，后续可在这里加入增量索引和持久化逻辑。
    """
    return vector_store.add_documents(documents)


def build_project_index(
    project_id: str,
    repo_path: str,
    config: AppConfig | None = None,
) -> RagIndex:
    """
    输入：
        project_id：项目 ID。
        repo_path：仓库根目录路径。
        config：可选应用配置，缺省时使用默认配置。
    输出：
        RagIndex：已构建完成的项目级索引对象。
    作用：
        串联代码加载、切块、Document 构建、embedding、vector store 创建和文档写入。
    为什么需要这个函数：
        建索引是 RAG indexing 层职责；Runtime 只应调用这个高层入口并保存 RagIndex，
        Retrieval 和 Graph 不应该读取文件、切块或重建向量存储。
    """
    app_config = config or AppConfig()
    file_records = load_code_files(repo_path)
    chunks = chunk_code_files(file_records)
    documents = [
        build_document(
            project_id=project_id,
            repo_path=repo_path,
            relative_path=str(chunk.get("relative_path", "")),
            content=str(chunk.get("content", "")),
            start_line=int(chunk.get("start_line", 0)),
            end_line=int(chunk.get("end_line", 0)),
        )
        for chunk in chunks
    ]
    vector_store = build_local_vector_store(build_embeddings(app_config))
    if documents:
        _index_documents(vector_store, documents)

    return RagIndex(
        project_id=project_id,
        repo_path=repo_path,
        vector_store=vector_store,
        document_count=len(documents),
    )
