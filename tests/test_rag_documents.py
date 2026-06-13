from src.rag.documents import LANGUAGE_BY_SUFFIX, build_document, infer_language


def test_rag_package_exports_new_standard_rag_components():
    import src.rag as rag

    assert rag.build_document is build_document
    assert hasattr(rag, "build_local_vector_store")
    assert hasattr(rag, "build_retriever")
    assert hasattr(rag, "index_documents")
    assert not hasattr(rag, "embed_chunks")
    assert not hasattr(rag, "build_index")
    assert not hasattr(rag, "search_index")


def test_infer_language_uses_module_level_suffix_mapping():
    assert LANGUAGE_BY_SUFFIX[".py"] == "python"
    assert infer_language("src/main.py") == "python"
    assert infer_language("README.md") == "markdown"
    assert infer_language("unknown.lock") == "text"


def test_build_document_preserves_code_metadata():
    doc = build_document(
        project_id="demo",
        repo_path="E:/repo",
        relative_path="src/main.py",
        content="print('hi')",
        start_line=1,
        end_line=1,
    )

    assert doc.page_content == "print('hi')"
    assert doc.metadata["project_id"] == "demo"
    assert doc.metadata["repo_path"] == "E:/repo"
    assert doc.metadata["relative_path"] == "src/main.py"
    assert doc.metadata["start_line"] == 1
    assert doc.metadata["end_line"] == 1
    assert doc.metadata["language"] == "python"
    assert doc.metadata["content_hash"]
