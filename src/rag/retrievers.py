from __future__ import annotations

from langchain_core.vectorstores import VectorStore, VectorStoreRetriever


def build_retriever(vector_store: VectorStore, top_k: int = 5) -> VectorStoreRetriever:
    """
    输入：
        vector_store：LangChain VectorStore 实例。
        top_k：每次检索返回的文档数量。
    输出：
        VectorStoreRetriever：LangChain retriever 对象。
    作用：
        从向量存储创建统一 retriever 接口。
    设计原因：
        Graph 和工具层后续只依赖 retriever，不直接依赖具体向量存储实现。
    """
    limit = max(1, int(top_k))
    return vector_store.as_retriever(search_kwargs={"k": limit})
