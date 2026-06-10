from __future__ import annotations

import hashlib

from src.core.config import EmbeddingConfig
from src.core.errors import ConfigurationError


class LocalHashEmbeddings:
    """
    输入：
        size：向量维度，默认 32。
    输出：
        LocalHashEmbeddings：本地 hash embedding 对象。
    作用：
        把文本稳定地转换成固定长度向量。
    设计原因：
        让 RAG 开发阶段可以离线运行，不依赖真实 embedding API。
    """

    def __init__(self, size: int = 32) -> None:
        self.size = size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        输入：
            texts：多段文本。
        输出：
            list[list[float]]：每段文本对应一个向量。
        作用：
            批量生成文档向量。
        设计原因：
            向量库通常一次接收多个文档向量，接口需要支持批量处理。
        """
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """
        输入：
            text：一段查询或文档文本。
        输出：
            list[float]：固定长度的向量。
        作用：
            为单段文本生成稳定向量。
        设计原因：
            RAG 检索时需要把用户问题也转换成向量，再和文档向量比较。
        """
        digest = hashlib.sha256(text.encode("utf-8")).digest()# 计算文本的 SHA-256 哈希值，得到一个字节串。
        values = []
        for index in range(self.size):
            # 把 hash 摘要的字节转换成 0-1 之间的浮点数，形成向量值。
            byte = digest[index % len(digest)]
            values.append(byte / 255.0)
        return values


def build_embeddings(config: EmbeddingConfig) -> LocalHashEmbeddings:
    """
    输入：
        config：EmbeddingConfig，包含 provider 和 model。
    输出：
        LocalHashEmbeddings：本地 embedding 实现。
    作用：
        根据配置创建 embedding 对象。
    设计原因：
        后续可以在这里扩展 OpenAI、阿里云或 HuggingFace embedding，而不用改 RAG 代码。
    """
    if config.provider != "local":
        raise ConfigurationError(f"unsupported embedding provider: {config.provider}")
    if config.model != "local-hash":
        raise ConfigurationError(f"unsupported local embedding model: {config.model}")
    return LocalHashEmbeddings()
