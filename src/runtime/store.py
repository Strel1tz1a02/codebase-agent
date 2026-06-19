from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.errors import ProjectNotFoundError

if TYPE_CHECKING:
    from src.runtime.project import Project


@dataclass
class RuntimeStore:

    projects: dict[str, Project] = field(default_factory=dict)
    storage_path: Path | None = None

    def __post_init__(self) -> None:
        if self.storage_path is not None:
            self.storage_path = _normalize_storage_path(self.storage_path)

    @classmethod
    def load(cls, storage_path: str | Path) -> RuntimeStore:
        from src.runtime.project import Project

        path = _normalize_storage_path(storage_path)
        if not path.exists():
            return cls(storage_path=path)

        data = json.loads(path.read_text(encoding="utf-8"))
        projects = {}
        for item in data.get("projects", []):
            if isinstance(item, dict):
                project = Project.from_payload(item)
                projects[project.project_id] = project
        return cls(projects=projects, storage_path=path)

    def save(self) -> None:
        if self.storage_path is None:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "projects": [_project_storage_payload(project) for project in self.list_projects()],
        }
        temp_path = self.storage_path.with_suffix(f"{self.storage_path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temp_path.replace(self.storage_path)# temp_path移动/重命名到storage_path；如果目标已存在，就替换掉它。

    def add_project(self, project: Project) -> None:
        self.projects[project.project_id] = project
        self.save()

    def list_projects(self) -> list[Project]:
        return list(self.projects.values())

    def get_project(self, project_id: str) -> Project:
        if project_id not in self.projects:
            raise ProjectNotFoundError(f"project not found: {project_id}")
        return self.projects[project_id]

    def delete_project(self, project_id: str) -> Project:
        project = self.get_project(project_id)
        del self.projects[project_id]
        self.save()
        return project


def _normalize_storage_path(storage_path: str | Path) -> Path:
    return Path(storage_path).expanduser().resolve()


def _project_storage_payload(project: Project) -> dict:
    """生成用于落盘的 project payload，并过滤没有 run 的空会话。"""
    payload = project.to_payload()
    payload["sessions"] = [
        session
        for session in payload.get("sessions", [])
        if isinstance(session, dict) and _has_non_empty_runs(session)
    ]
    return payload


def _has_non_empty_runs(session_payload: dict) -> bool:
    """校验 session payload 里存在非空 runs 列表，避免空会话被持久化。"""
    runs = session_payload.get("runs")
    return isinstance(runs, list) and len(runs) > 0
