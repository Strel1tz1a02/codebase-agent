from pathlib import Path

import src.rag.retrieval as retrieval


def test_retrieve_relevant_chunks_uses_new_langchain_rag_pipeline(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    source = repo / "src" / "main.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def run_agent_loop():\n"
        "    return 'tool execution complete'\n",
        encoding="utf-8",
    )

    def fail_if_legacy_pipeline_is_used(*_args, **_kwargs):
        raise AssertionError("legacy hash embedding/index/cache pipeline should not be used")

    monkeypatch.setattr(retrieval, "embed_chunks", fail_if_legacy_pipeline_is_used, raising=False)
    monkeypatch.setattr(retrieval, "embed_query_text", fail_if_legacy_pipeline_is_used, raising=False)
    monkeypatch.setattr(retrieval, "build_index", fail_if_legacy_pipeline_is_used, raising=False)
    monkeypatch.setattr(retrieval, "search_index", fail_if_legacy_pipeline_is_used, raising=False)
    monkeypatch.setattr(retrieval, "load_index_cache", fail_if_legacy_pipeline_is_used, raising=False)
    monkeypatch.setattr(retrieval, "save_index_cache", fail_if_legacy_pipeline_is_used, raising=False)

    results = retrieval.retrieve_relevant_chunks(
        question="How does run_agent_loop finish tool execution?",
        repo_path=str(repo),
        top_k=1,
        reindex=True,
    )

    assert len(results) == 1
    assert Path(str(results[0]["relative_path"])).as_posix() == "src/main.py"
    assert results[0]["start_line"] == 1
    assert results[0]["end_line"] == 2
    assert "run_agent_loop" in str(results[0]["content"])
    assert isinstance(results[0]["score"], float)
