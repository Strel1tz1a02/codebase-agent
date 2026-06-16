from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """
    输入：
        provider：模型服务商名称，例如 aliyun、deepseek。
        model：具体模型名称，例如 qwen-plus。
        api_key_env：保存 API Key 的环境变量名。
        base_url：OpenAI-compatible 接口地址，可为空。
        temperature：模型回答随机性，数值越低越稳定。
    输出：
        ModelConfig：规范化后的模型配置对象。
    作用：
        集中保存 LLM 模型相关配置。
    设计原因：
        让后续模型工厂、Graph 节点不直接关心 CLI 参数或环境变量细节。
    """

    provider: str = "aliyun"
    model: str = "qwen-plus"
    api_key_env: str = "CODEBASE_AGENT_API_KEY"
    base_url: str = ""
    temperature: float = 0.2

    def __post_init__(self) -> None:
        """
        输入：
            self：刚创建好的 ModelConfig 对象。
        输出：
            None，直接更新 self.provider。
        作用：
            把 provider 去掉首尾空格并转换成小写。
        设计原因：
            用户可能输入 Aliyun、 aliyun 等形式，统一后方便后续查 provider 注册表。
        """
        self.provider = self.provider.strip().lower()


@dataclass
class EmbeddingConfig:
    """
    输入：
        provider：embedding 服务商名称，例如 local、openai、aliyun。
        model：embedding 模型名称，例如 local-hash。
    输出：
        EmbeddingConfig：规范化后的 embedding 配置对象。
    作用：
        集中保存 RAG 向量化阶段需要的 embedding 配置。
    设计原因：
        让后续 embedding factory 可以根据配置创建不同实现，而不是在 RAG 代码里写死模型。
    """

    provider: str = "local"
    model: str = "local-hash"

    def __post_init__(self) -> None:
        """
        输入：
            self：刚创建好的 EmbeddingConfig 对象。
        输出：
            None，直接更新 self.provider。
        作用：
            把 provider 去掉首尾空格并转换成小写。
        设计原因：
            用户可能输入 Local、 local 等形式，统一后方便后续查 embedding provider。
        """
        self.provider = self.provider.strip().lower()


@dataclass
class VectorStoreConfig:
    """
    输入：
        provider：向量存储后端名称，例如 local、qdrant、milvus。
        persist_dir：本地向量索引保存目录。
    输出：
        VectorStoreConfig：规范化后的向量存储配置对象。
    作用：
        集中保存 RAG 向量存储阶段需要的配置。
    设计原因：
        让后续 vector store factory 可以根据配置切换本地或生产向量库。
    """

    provider: str = "local"
    persist_dir: str = ".codebase_agent/vectorstores"

    def __post_init__(self) -> None:
        """
        输入：
            self：刚创建好的 VectorStoreConfig 对象。
        输出：
            None，直接更新 self.provider。
        作用：
            把 provider 去掉首尾空格并转换成小写。
        设计原因：
            用户可能输入 Local、 local 等形式，统一后方便后续查向量存储后端。
        """
        self.provider = self.provider.strip().lower()


@dataclass
class RetrievalConfig:
    """
    输入：
        top_k：每次检索返回的代码片段数量。
    输出：
        RetrievalConfig：规范化后的检索配置对象。
    作用：
        控制 RAG 检索阶段返回多少条上下文。
    设计原因：
        检索结果太少会缺上下文，太多会浪费 token；集中配置便于后续调整。
    """

    top_k: int = 5

    def __post_init__(self) -> None:
        """
        输入：
            self：刚创建好的 RetrievalConfig 对象。
        输出：
            None，直接更新 self.top_k。
        作用：
            把 top_k 限制在 1 到 20 之间。
        设计原因：
            防止无效参数导致检索为空，或一次返回过多代码片段。
        """
        self.top_k = max(1, min(self.top_k, 20))


@dataclass
class AppConfig:
    """
    输入：
        model：LLM 模型配置。
        embeddings：RAG embedding 配置。
        vector_store：RAG 向量存储配置。
        retrieval：RAG 检索配置。
    输出：
        AppConfig：应用级总配置对象。
    作用：
        把 codebase-agent 的核心配置组合到一个入口。
    设计原因：
        后续 API、CLI、Runtime 可以只传递 AppConfig，而不是到处传多个零散配置对象。
    """

    model_config: ModelConfig = field(default_factory=ModelConfig)
    embeddings_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    retrieval_config: RetrievalConfig = field(default_factory=RetrievalConfig)
