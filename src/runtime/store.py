from __future__ import annotations

from dataclasses import dataclass, field

from src.rag.schemas import RagIndex
from src.runtime.projects import Project


@dataclass
class RuntimeStore:
    """
    输入：
        projects：按 project_id 保存的项目字典。
        project_indexes：按 project_id 保存的项目级 RAG 索引字典。
    输出：
        RuntimeStore 数据对象。
    作用：
        作为 RuntimeService 的统一对象存储入口，持有 project 根对象和项目级 RagIndex。
    为什么需要这个类：
        Runtime 需要按 project_id 快速取得已构建索引；保存 RagIndex 而不是 callable retriever，
        可以让召回职责留在 RAG retrieval 层。
    """

    projects: dict[str, Project] = field(default_factory=dict)
    project_indexes: dict[str, RagIndex] = field(default_factory=dict)
