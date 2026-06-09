from __future__ import annotations

from uuid import uuid4

from src.runtime.session import Session


class SessionMemory:
    """
    输入：
        无。
    输出：
        SessionMemory 对象。
    作用：
        在当前 Python 进程内管理 Session 记忆。
    设计原因：
        V6 先学习 Runtime 的会话记忆管理，不引入数据库或持久化。
    """

    def __init__(self) -> None:
        """
        输入：
            无。
        输出：
            无。
        作用：
            初始化内存字典，用 session_id 保存 Session。
        设计原因：
            内存 memory 足够支撑 V6 和后续 V7 API 的第一版演示。
        """
        self._sessions: dict[str, Session] = {}

    def create_session(self, repo_path: str) -> Session:
        """
        输入：
            repo_path：当前会话绑定的仓库路径。
        输出：
            Session：新创建的会话对象。
        作用：
            创建一个空会话，并放入内存 memory。
        设计原因：
            Runtime 需要先有 session_id，后续提问才能追加到同一个上下文里。
        """
        session = Session(
            session_id=uuid4().hex,
            repo_path=repo_path,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Session:
        """
        输入：
            session_id：会话 ID。
        输出：
            Session：对应的会话对象。
        作用：
            从内存 memory 读取已有会话。
        设计原因：
            AgentRuntime.ask 需要根据 session_id 找回 repo_path、messages 和 trace。
        """
        if session_id not in self._sessions:
            raise KeyError(f"session not found: {session_id}")
        return self._sessions[session_id]
