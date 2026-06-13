from langchain_core.embeddings import DeterministicFakeEmbedding

from src.rag.documents import build_document
from src.rag.indexing import index_documents
from src.rag.retrievers import build_retriever
from src.rag.vectorstores import build_local_vector_store


def test_index_documents_makes_documents_retrievable():
    store = build_local_vector_store(DeterministicFakeEmbedding(size=8))
    doc = build_document(
        project_id="demo",
        repo_path="E:/repo",
        relative_path="src/main.py",
        content="def run_agent(): pass",
        start_line=1,
        end_line=1,
    )

    ids = index_documents(store, [doc])
    retriever = build_retriever(store, top_k=1)
    results = retriever.invoke("run_agent")

    assert len(ids) == 1
    assert len(results) == 1
    assert results[0].metadata["relative_path"] == "src/main.py"
