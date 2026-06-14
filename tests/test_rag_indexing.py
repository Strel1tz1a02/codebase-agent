from src.rag.indexing import build_project_index
from src.rag.schemas import RagIndex


def test_build_project_index_returns_rag_index(tmp_path):
    repo_file = tmp_path / "app.py"
    repo_file.write_text("def entrypoint():\n    return 'ok'\n", encoding="utf-8")

    index = build_project_index("demo", str(tmp_path))

    assert isinstance(index, RagIndex)
    assert index.project_id == "demo"
    assert index.repo_path == str(tmp_path)
    assert index.document_count >= 1
