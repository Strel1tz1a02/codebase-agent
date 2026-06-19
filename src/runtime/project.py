from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.core.errors import SessionNotFoundError
from src.rag.schemas import RagIndex
from src.runtime.session import RuntimeSession


@dataclass
class Project:
    """
    输入：
        project_id：项目唯一标识。
        name：用户可读的项目名称。
        repo_path：项目绑定的本地仓库路径。
        index_status：RAG 索引状态。
    输出：
        Project 数据对象。
    作用：
        表示一个被 codebase-agent 注册和分析的代码仓库。
    为什么需要这个类：
        成熟 Runtime 不能只围绕一次 ask 工作；需要先有 project，后续 session、run 和 index 都绑定到它。
    """

    project_id: str
    name: str
    repo_path: str
    index_status: Literal["not_indexed", "indexing", "indexed", "failed"] = "not_indexed"
    index: RagIndex | None = None
    sessions: dict[str, RuntimeSession] = field(default_factory=dict)

    def add_session(self, session: RuntimeSession) -> None:
        """把 session 挂到当前 project 下。"""
        self.sessions[session.session_id] = session

    def get_session(self, session_id: str) -> RuntimeSession:
        """按 session_id 读取 session，不存在时抛出领域异常。"""
        if session_id not in self.sessions:
            raise SessionNotFoundError(f"session not found: {session_id}")
        return self.sessions[session_id]

    def to_payload(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "repo_path": self.repo_path,
            "index_status": _persisted_index_status(self.index_status),
            "sessions": [session.to_payload() for session in self.sessions.values()],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Project:
        project = cls(
            project_id=str(payload.get("project_id", "")),
            name=str(payload.get("name", "")),
            repo_path=str(payload.get("repo_path", "")),
            index_status=_persisted_index_status(payload.get("index_status", "not_indexed")),  # type: ignore[arg-type]
        )
        for item in payload.get("sessions", []):
            if isinstance(item, dict):
                project.add_session(RuntimeSession.from_payload(item))
        return project


def _persisted_index_status(status: object) -> str:
    normalized = str(status)
    if normalized in {"indexed", "indexing"}:
        return "not_indexed"
    if normalized in {"not_indexed", "failed"}:
        return normalized
    return "not_indexed"
