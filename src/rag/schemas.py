from __future__ import annotations

from dataclasses import dataclass

from langchain_core.vectorstores import VectorStore


@dataclass
class RagIndex:
    """
    输入：
        project_id：索引所属项目 ID。
        repo_path：索引对应的仓库根路径。
        vector_store：已经写入文档的 LangChain VectorStore。
        document_count：索引中的文档数量。
    输出：
        RagIndex 领域对象。
    作用：
        表示一个已经构建完成、可用于召回的项目级 RAG 索引。
    为什么需要这个类：
        Runtime 和 Graph 需要传递“已构建索引”这个领域对象，而不是传递 callable retriever 或重建索引所需的零散参数。
    """

    project_id: str
    repo_path: str
    vector_store: VectorStore
    document_count: int


@dataclass
class RagHit:
    """
    输入：
        relative_path：命中文档所在的仓库相对路径。
        start_line：命中片段起始行号。
        end_line：命中片段结束行号。
        content：命中的代码或文本内容。
        score：召回分数；当前 retriever 无原生分数时使用默认值。
    输出：
        RagHit 领域对象。
    作用：
        表示一次 RAG 召回命中的标准结果。
    为什么需要这个类：
        RAG 层需要稳定的领域返回值，Graph/API/CLI 可按需转换为 dict，而不是直接依赖 LangChain Document。
    """

    relative_path: str
    start_line: int
    end_line: int
    content: str
    score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """
        输入：
            self：当前 RagHit 对象。
        输出：
            dict：兼容 graph 现有 retrieval_hits 的字典结构。
        作用：
            将 RAG 领域对象转换成现有回答链路可消费的结构。
        为什么需要这个函数：
            兼容层需要保留旧 dict 协议，同时让 RAG 内部使用更清晰的领域对象。
        """
        return {
            "relative_path": self.relative_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "score": self.score,
        }
