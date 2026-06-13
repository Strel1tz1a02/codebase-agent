from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore


def index_documents(vector_store: VectorStore, documents: list[Document]) -> list[str]:
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
