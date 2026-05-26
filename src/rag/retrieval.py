from __future__ import annotations

from src.rag.chunker import chunk_code_files
from src.rag.code_loader import load_code_files
from src.rag.embeddings import embed_chunks, embed_query_text
from src.rag.index import build_index, search_index
from src.rag.store import (
    compute_repo_fingerprint,
    is_cache_valid,
    load_index_cache,
    save_index_cache,
)


def retrieve_relevant_chunks(
    question: str,
    repo_path: str,
    top_k: int = 5,
    reindex: bool = False,
) -> list[dict[str, object]]:
    """
    输入：
        question：用户问题文本。
        repo_path：仓库根目录路径。
        top_k：检索返回数量上限。
        reindex：是否强制忽略缓存并重建索引。
    输出：
        list[dict[str, object]]：命中 chunks，包含路径、行号、内容和 score。
    作用：
        串联 chunk -> embed -> index -> top-k 检索流程（优先复用缓存）。
    设计原因：
        在保证链路完整的同时降低重复构建开销，便于迭代调试。
    """
    file_records = load_code_files(repo_path)
    repo_fingerprint = compute_repo_fingerprint(file_records)
    config = {"top_k": int(top_k)}

    cache = None
    if not reindex:
        cache = load_index_cache(repo_path)

    if is_cache_valid(cache, repo_fingerprint, config):
        chunks = list(cache.get("chunks", []))
        index_rows = list(cache.get("index_rows", []))
        build_index(index_rows)
    else:
        chunks = chunk_code_files(file_records)
        embedded_chunks = embed_chunks(chunks)
        index_rows = build_index(embedded_chunks)
        save_index_cache(
            repo_path=repo_path,
            repo_fingerprint=repo_fingerprint,
            chunks=chunks,
            embedded_chunks=embedded_chunks,
            index_rows=index_rows,
            config=config,
        )

    query_vector = embed_query_text(question)
    hits = search_index(query_vector, top_k=top_k)
    if not hits:
        return []

    chunks_by_id: dict[str, dict[str, object]] = {str(chunk.get("id", "")): chunk for chunk in chunks}
    results: list[dict[str, object]] = []
    for hit in hits:
        chunk = chunks_by_id.get(str(hit.get("id", "")))
        if chunk is None:
            continue
        item = dict(chunk)
        item["score"] = float(hit.get("score", 0.0))
        results.append(item)
    return results
