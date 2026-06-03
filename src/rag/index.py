from __future__ import annotations

import math

_INDEX_ROWS: list[dict[str, object]] = []


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    输入：
        vec_a：向量 A。
        vec_b：向量 B。
    输出：
        float：余弦相似度分数。
    作用：
        计算查询向量与候选向量的相似度。
    设计原因：
        top-k 检索先用纯 Python 余弦相似度实现，便于离线验证。
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def build_index(embedded_chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    """
    输入：
        embedded_chunks：embedding 结果列表。
    输出：
        list[dict[str, object]]：构建后的索引行列表。
    作用：
        把向量化结果放入内存索引。
    设计原因：
        后续 search 直接在内存索引上做 top-k，相比重复传参更简洁。
    """
    global _INDEX_ROWS
    rows: list[dict[str, object]] = []
    for item in embedded_chunks:
        rows.append(
            {
                "id": str(item.get("id", "")),
                "vector": list(item.get("vector", [])),
                "metadata": dict(item.get("metadata", {})),
            }
        )
    rows.sort(key=lambda row: str(row["id"]))
    _INDEX_ROWS = rows
    return list(_INDEX_ROWS)


def search_index(query_vector: list[float], top_k: int = 5) -> list[dict[str, object]]:
    """
    输入：
        query_vector：查询向量。
        top_k：返回命中条数上限。
    输出：
        list[dict[str, object]]：命中结果，包含 id/score/metadata。
    作用：
        从内存索引中按余弦相似度检索 top-k。
    设计原因：
        先验证检索正确性与排序稳定性，再考虑接入向量库。
    """
    limit = max(0, int(top_k))
    scored: list[dict[str, object]] = []
    for row in _INDEX_ROWS:
        score = _cosine_similarity(query_vector, list(row.get("vector", [])))
        scored.append(
            {
                "id": str(row.get("id", "")),
                "score": score,
                "metadata": dict(row.get("metadata", {})),
            }
        )
    scored.sort(key=lambda item: (-float(item["score"]), str(item["id"])))
    return scored[:limit]
