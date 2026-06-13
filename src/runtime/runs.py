from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from src.core.errors import ProjectNotFoundError
from src.graph.builder import build_graph
from src.graph.state import create_initial_state
from src.runtime.events import RunEvent
from src.runtime.projects import Project
from src.runtime.sessions import RuntimeSession
from src.runtime.store import RuntimeStore


'''
    Project -> RuntimeSession -> Run -> RunEvent

    Project：一个已注册的代码仓库。
    Session：围绕某个 Project 的一段对话。
    Run：Session 中的一次用户提问，对应一次 LangGraph 执行。
    Event：记录一次 Run 执行过程中的事件。
'''

@dataclass
class Run:
    """
    输入：
        run_id：run 唯一标识。
        session_id：run 所属 session。
        question：本次用户问题。
        status：run 当前状态。
        answer：graph 生成的最终回答。
        reason：失败或停止原因。
    输出：
        Run 数据对象。
    作用：
        表示用户一次提问对应的一次 graph 执行。
    为什么需要这个类：
        成熟 Runtime 需要把“提问”和“执行过程”显式建模，便于查询状态、记录事件和后续支持异步执行。
    """

    run_id: str
    session_id: str
    question: str
    status: Literal["queued", "running", "completed", "failed", "stopped"] = "queued"
    answer: str = ""
    reason: str = ""
    events: list[RunEvent] = field(default_factory=list)


class RuntimeService:
    """
    输入：
        graph：可选的 LangGraph compiled graph 或 fake graph。
    输出：
        RuntimeService 服务对象。
    作用：
        在内存中管理 project、session、run 和 run event，并负责调用 graph。
    为什么需要这个类：
        API 和 CLI 后续都应调用同一个 RuntimeService，避免各入口重复拼接 project/session/run 生命周期。
    """

    def __init__(self, graph: object | None = None) -> None:
        self.graph = graph or build_graph()
        self.store = RuntimeStore()

    def create_project(self, name: str, repo_path: str) -> Project:
        """
        输入：
            name：项目名称。
            repo_path：本地仓库路径。
        输出：
            Project：新创建的项目对象。
        作用：
            注册一个可被分析的代码仓库。
        为什么需要这个函数：
            session 和 run 都需要绑定 project；先注册 project 可以让后续 API/CLI 使用稳定 project_id。
        """
        project = Project(
            project_id=uuid4().hex,
            name=name,
            repo_path=repo_path,
        )
        self.store.projects[project.project_id] = project
        return project

    def get_project(self, project_id: str) -> Project:
        """
        输入：
            project_id：项目 ID。
        输出：
            Project：对应项目对象。
        作用：
            从内存存储中读取已注册项目。
        为什么需要这个函数：
            session 创建、graph 执行和后续 index 都需要根据 project_id 找到 repo_path。
        """
        self.validate_project_exists(project_id)
        return self.store.projects[project_id]

    def validate_project_exists(self, project_id: str) -> None:
        """
        输入：
            project_id：项目 ID。
        输出：
            None；项目不存在时抛出 ProjectNotFoundError。
        作用：
            明确校验 project_id 是否引用了已注册项目。
        为什么需要这个函数：
            create_session 只需要做引用完整性校验，不应该用 get_project 表达校验语义。
        """
        if project_id not in self.store.projects:
            raise ProjectNotFoundError(f"project not found: {project_id}")

    def create_session(self, project_id: str) -> RuntimeSession:
        """
        输入：
            project_id：要绑定的项目 ID。
        输出：
            RuntimeSession：新创建的会话对象。
        作用：
            创建一个围绕指定 project 的对话容器。
        为什么需要这个函数：
            用户后续每次提问都应落到某个 session 下，而不是直接散落成无上下文 run。
        """
        project = self.get_project(project_id)
        session = RuntimeSession(
            session_id=uuid4().hex,
            project_id=project_id,
        )
        project.sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> RuntimeSession:
        """
        输入：
            session_id：会话 ID。
        输出：
            RuntimeSession：对应会话对象。
        作用：
            从内存存储中读取已创建 session。
        为什么需要这个函数：
            创建 run 和执行 graph 时都需要从 session 找回 project_id。
        """
        self.validate_session_exists(session_id)
        session = self._find_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        return session

    def validate_session_exists(self, session_id: str) -> None:
        """
        输入：
            session_id：会话 ID。
        输出：
            None；session 不存在时抛出 KeyError。
        作用：
            明确校验 session_id 是否引用了已创建会话。
        为什么需要这个函数：
            create_run 只是在创建前检查外键关系，不需要读取 session 对象；单独函数让语义更直接。
        """
        if self._find_session(session_id) is None:
            raise KeyError(f"session not found: {session_id}")

    def ask(self, session_id: str, question: str) -> Run:
        """
        输入：
            session_id：用户本轮问题所属的会话 ID。
            question：用户本轮问题。
        输出：
            Run：已经完成 graph 执行并更新状态的 run。
        作用：
            统一对外提供“提问并执行”的高层入口。
        为什么需要这个函数：
            API/CLI 不应该重复拼接 create run 和 run graph 两步；它们只需要关心一次提问的最终 run 结果。
        """
        run = self._create_run(session_id, question)
        return self._run_graph(run.run_id)

    def _create_run(self, session_id: str, question: str) -> Run:
        """
        输入：
            session_id：run 所属会话 ID。
            question：用户本轮问题。
        输出：
            Run：新创建且状态为 queued 的 run。
        作用：
            为一次用户提问创建可追踪执行记录。
        为什么需要这个函数：
            run 是 graph 执行的最小可查询单位，后续 API 可通过 run_id 查询状态和事件。
        """
        session = self.get_session(session_id)
        run = Run(
            run_id=uuid4().hex,
            session_id=session_id,
            question=question,
        )
        session.runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> Run:
        """
        输入：
            run_id：run ID。
        输出：
            Run：对应 run 对象。
        作用：
            从内存存储中读取 run。
        为什么需要这个函数：
            事件追加、graph 执行和 API 查询都需要统一读取 run。
        """
        self.validate_run_exists(run_id)
        run = self._find_run(run_id)
        if run is None:
            raise KeyError(f"run not found: {run_id}")
        return run

    def validate_run_exists(self, run_id: str) -> None:
        """
        输入：
            run_id：run ID。
        输出：
            None；run 不存在时抛出 KeyError。
        作用：
            明确校验 run_id 是否引用了已创建 run。
        为什么需要这个函数：
            追加事件和查询事件只需要先确认 run 存在，单独函数比调用 get_run 更能表达校验意图。
        """
        if self._find_run(run_id) is None:
            raise KeyError(f"run not found: {run_id}")

    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> RunEvent:
        """
        输入：
            run_id：事件所属 run。
            event_type：事件类型。
            payload：事件详情。
        输出：
            RunEvent：新追加的事件对象。
        作用：
            给某次 run 追加一条结构化事件。
        为什么需要这个函数：
            事件写入规则应集中在 RuntimeService，避免 graph/API/CLI 各自维护不同事件格式。
        """
        run = self.get_run(run_id)
        event = RunEvent(
            event_id=uuid4().hex,
            run_id=run_id,
            event_type=event_type,
            payload=dict(payload or {}),
        )
        run.events.append(event)
        return event

    def list_run_events(self, run_id: str) -> list[RunEvent]:
        """
        输入：
            run_id：run ID。
        输出：
            list[RunEvent]：该 run 的事件快照。
        作用：
            查询一次 run 的执行轨迹。
        为什么需要这个函数：
            API 后续需要提供 run events 查询接口；这里先给出内存版读取能力。
        """
        run = self.get_run(run_id)
        return list(run.events)

    def _run_graph(self, run_id: str) -> Run:
        """
        输入：
            run_id：要执行的 run ID。
        输出：
            Run：执行后更新状态和答案的 run。
        作用：
            把 run 转换成 graph state，调用 graph，并记录开始、内部和结束事件。
        为什么需要这个函数：
            Runtime 是 session/run 生命周期和 LangGraph 执行之间的边界；集中在这里接入 graph，API/CLI 就不用关心 graph 细节。
        """
        run = self.get_run(run_id)
        run.status = "running"
        self.append_event(run_id, "graph_start", {"run_id": run_id})

        session = self.get_session(run.session_id)
        project = self.get_project(session.project_id)
        state = create_initial_state(
            project_id=project.project_id,
            repo_path=project.repo_path,
            question=run.question,
        )
        result = self.graph.invoke(state)  # type: ignore[attr-defined]

        for event in result.get("events", []):
            if isinstance(event, dict):
                self.append_event(run_id, "graph_event", event)

        run.status = str(result.get("status", "completed"))  # type: ignore[assignment]
        run.answer = str(result.get("answer", ""))
        run.reason = str(result.get("reason", ""))
        self.append_event(run_id, "graph_finish", {"status": run.status})
        return run

    def _find_session(self, session_id: str) -> RuntimeSession | None:
        """
        输入：
            session_id：会话 ID。
        输出：
            RuntimeSession 或 None。
        作用：
            从 project -> sessions 嵌套结构中按 ID 查找 session。
        为什么需要这个函数：
            当前阶段优先保持所有权结构清晰，不提前维护全局 session 索引；查找先用简单遍历实现。
        """
        for project in self.store.projects.values():
            session = project.sessions.get(session_id)
            if isinstance(session, RuntimeSession):
                return session
        return None

    def _find_run(self, run_id: str) -> Run | None:
        """
        输入：
            run_id：Run ID。
        输出：
            Run 或 None。
        作用：
            从 project -> sessions -> runs 嵌套结构中按 ID 查找 run。
        为什么需要这个函数：
            当前阶段不引入 runs_by_id 全局索引，让对象归属关系先由嵌套结构表达清楚。
        """
        for project in self.store.projects.values():
            for session in project.sessions.values():
                if isinstance(session, RuntimeSession):
                    run = session.runs.get(run_id)
                    if isinstance(run, Run):
                        return run
        return None
