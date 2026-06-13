from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore


def build_local_vector_store(embeddings: Embeddings) -> InMemoryVectorStore:
    """
    输入：
        embeddings：LangChain Embeddings 实现。
    输出：
        InMemoryVectorStore：本地内存向量存储。
    作用：
        创建可用于开发和测试的本地 VectorStore。
    设计原因：
        第一版 RAG 标准化需要离线可运行，同时保留后续替换 Qdrant、Milvus、pgvector 的边界。
    """
    return InMemoryVectorStore(embedding=embeddings)
