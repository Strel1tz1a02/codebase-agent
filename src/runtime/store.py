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

    projects: dict[str, Project] = field(default_factory=dict)# field(default_factory=dict) 是 dataclass 中的一种用法，用于为字段提供一个默认的工厂函数。在这里，它为 projects 字段提供了一个默认的空字典。当创建 RuntimeStore 实例时，如果没有提供 projects 参数，它将自动初始化为一个空字典。这种方式比直接使用 projects: dict[str, Project] = {} 更安全，因为后者会在所有实例之间共享同一个字典，而 field(default_factory=dict) 则确保每个实例都有自己的独立字典。