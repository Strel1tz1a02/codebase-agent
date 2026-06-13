from langchain_core.embeddings import DeterministicFakeEmbedding

from src.rag.vectorstores import build_local_vector_store


def test_build_local_vector_store_supports_similarity_search():
    store = build_local_vector_store(DeterministicFakeEmbedding(size=8))
    store.add_texts(["alpha", "beta"])

    results = store.similarity_search("alpha", k=1)

    assert len(results) == 1
