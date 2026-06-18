from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.errors import ProjectNotFoundError

if TYPE_CHECKING:
    from src.runtime.project import Project

@dataclass
class RuntimeStore:
    """
    输入：
        projects：按 project_id 保存的项目字典。
    输出：
        RuntimeStore 数据对象。
    作用：
        作为 RuntimeService 的统一对象存储入口，只持有 project 根对象。
    为什么需要这个类：
        Runtime 的对象所有权从 project 开始向下展开；项目级索引由 Project 自己维护，
        store 不再维护并列的 project -> index 字典。
    """

    projects: dict[str, Project] = field(default_factory=dict)

    def add_project(self, project: Project) -> None:
        self.projects[project.project_id] = project

    def get_project(self, project_id: str) -> Project:
        if project_id not in self.projects:
            raise ProjectNotFoundError(f"project not found: {project_id}")
        return self.projects[project_id]
    
