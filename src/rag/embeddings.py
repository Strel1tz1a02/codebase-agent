from __future__ import annotations

import hashlib
import math

DEFAULT_EMBEDDING_DIM = 128


def _normalize_vector(vector: list[float]) -> list[float]:
    """
    输入：
        vector：原始向量。
    输出：
        list[float]：L2 归一化后的向量。
    作用：
        统一向量尺度，便于后续相似度计算。
    设计原因：
        检索阶段通常基于余弦相似度，归一化后分数更稳定。
    """
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def _hash_embed_text(text: str, dim: int) -> list[float]:
    """
    输入：
        text：待向量化文本。
        dim：向量维度。
    输出：
        list[float]：确定性向量。
    作用：
        把文本映射到固定维度空间，供离线检索验证使用。
    设计原因：
        在不接外部 embedding API 的阶段先跑通链路，后续可无缝替换真实模型。
    """
    if dim <= 0:
        dim = 1

    vector = [0.0] * dim
    tokens = text.split()
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    return _normalize_vector(vector)


def embed_chunks(chunks: list[dict[str, object]], dim: int = DEFAULT_EMBEDDING_DIM) -> list[dict[str, object]]:
    """
    输入：
        chunks：chunk 列表，每项包含 id/content 等字段。
        dim：向量维度。
    输出：
        list[dict[str, object]]：embedding 结果列表，结构为 {id, vector, metadata}。
    作用：
        将 chunk 文本向量化，产出可索引的数据。
    设计原因：
        为索引层提供统一输入结构，解耦切分与检索模块。
    """
    results: list[dict[str, object]] = []
    for chunk in chunks:
        results.append(
            {
                "id": str(chunk.get("id", "")),
                "vector": _hash_embed_text(str(chunk.get("content", "")), dim),
                "metadata": {
                    "file_path": str(chunk.get("file_path", "")),
                    "relative_path": str(chunk.get("relative_path", "")),
                    "start_line": int(chunk.get("start_line", 0)),
                    "end_line": int(chunk.get("end_line", 0)),
                    "content": str(chunk.get("content", "")),
                },
            }
        )
    return results


def embed_query_text(question: str, dim: int = DEFAULT_EMBEDDING_DIM) -> list[float]:
    """
    输入：
        question：查询问题文本。
        dim：向量维度。
    输出：
        list[float]：查询向量。
    作用：
        为 top-k 检索生成查询向量。
    设计原因：
        查询向量与 chunk 向量必须在同一向量空间，才能比较相似度。
    """
    return _hash_embed_text(question, dim)
