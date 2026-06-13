from __future__ import annotations

from dataclasses import dataclass, field

from src.runtime.projects import Project


@dataclass
class RuntimeStore:
    """
    输入：
        projects：按 project_id 保存的项目字典。
    输出：
        RuntimeStore 数据对象。
    作用：
        作为 RuntimeService 的统一对象存储入口，持有所有 project 根对象。
    为什么需要这个类：
        Runtime 的对象所有权从 project 开始向下展开；集中入口可以让 RuntimeService 只依赖 graph 和 store，
        避免再维护平铺的 session、run、event 字典。
    """

    projects: dict[str, Project] = field(default_factory=dict)
