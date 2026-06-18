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
        """把 project 写入 store。"""
        self.projects[project.project_id] = project

    def list_projects(self) -> list[Project]:
        """按插入顺序返回所有 project。"""
        return list(self.projects.values())

    def get_project(self, project_id: str) -> Project:
        """按 project_id 读取 project，不存在时抛出领域异常。"""
        if project_id not in self.projects:
            raise ProjectNotFoundError(f"project not found: {project_id}")
        return self.projects[project_id]

    def delete_project(self, project_id: str) -> Project:
        """删除并返回指定 project，不存在时抛出领域异常。"""
        project = self.get_project(project_id)
        del self.projects[project_id]
        return project
