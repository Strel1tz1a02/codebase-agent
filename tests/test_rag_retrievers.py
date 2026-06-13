from langchain_core.embeddings import DeterministicFakeEmbedding

from src.rag.retrievers import build_retriever
from src.rag.vectorstores import build_local_vector_store


def test_build_retriever_returns_top_k_documents():
    store = build_local_vector_store(DeterministicFakeEmbedding(size=8))
    store.add_texts(["alpha", "beta"])
    retriever = build_retriever(store, top_k=1)

    results = retriever.invoke("alpha")

    assert len(results) == 1
