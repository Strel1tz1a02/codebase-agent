from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from typing import Literal
from uuid import uuid4

from src.core.config import AppConfig
from src.core.errors import RagIndexNotReadyError
from src.graph.builder import build_graph
from src.graph.state import create_initial_state
from src.models.chat import build_chat_model
from src.rag.indexing import build_project_index
from src.rag.schemas import RagIndex
from src.runtime.events import RunEvent
from src.runtime.sessions import RuntimeSession
from src.runtime.store import RuntimeStore
from src.tools.toolkit import execute_tool

if TYPE_CHECKING:
    from src.runtime.projects import Project

"""
Project -> RuntimeSession -> Run -> RunEvent

Project：一个已注册的代码仓库。
Session：围绕某个 Project 的一段对话。
Run：Session 中的一次用户提问，对应一次 LangGraph 执行。
Event：记录一次 Run 执行过程中的事件。
"""


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
        events：run 拥有的事件列表。
    输出：
        Run 数据对象。
    作用：
        表示用户一次提问对应的一次 graph 执行。
    为什么需要这个类：
        成熟 Runtime 需要把“提问”和“执行过程”显式建模，便于查询状态、记录事件和后续支持异步执行。
    """

    run_id: str
    session_id: str = ""
    question: str = ""
    status: Literal["queued", "running", "completed", "failed", "stopped"] = "queued"
    answer: str = ""
    reason: str = ""
    events: list[RunEvent] = field(default_factory=list)

    def add_event(self,event: RunEvent) -> None:
        self.events.append(event)
    
    def list_events(self) -> list[RunEvent]:
        return list(self.events)


class RuntimeService:
    """
    输入：
        graph：可选的 LangGraph compiled graph 或 fake graph。
    输出：
        RuntimeService 服务对象。
    作用：
        在内存中管理 project、session、run 和 run event，并负责调用 graph。
    为什么需要这个类：
        RuntimeService 只维护 graph 和 store；project/session/run 的读取必须沿所有权路径进行，
        避免重新退回全局平铺索引或全局遍历查找。
    """

    def __init__(
        self,
        graph: object | None = None,
        config: AppConfig | None = None,
        chat_model: object | None = None,
        tool_executor:callable | None = None,
    ) -> None:
        self.graph = graph or build_graph()
        self.config = config or AppConfig()
        self.chat_model = chat_model or build_chat_model(self.config)
        self.tool_executor = tool_executor or execute_tool
        self.store = RuntimeStore()

    def create_project(self, project_name: str, repo_path: str) -> Project:
        project = Project(project_id=uuid4().hex, name=project_name, repo_path=repo_path)
        self.store.add_project(project)
        return project

    def get_project(self, project_id: str) -> Project:
        return self.store.get_project(project_id)

    def create_session(self, project_id: str) -> RuntimeSession:
        session = RuntimeSession(session_id=uuid4().hex)
        self.store.get_project(project_id).add_session(session)
        return session

    def get_session(self, project_id: str, session_id: str) -> RuntimeSession:
        return self.store.get_project(project_id).get_session(session_id)

    def get_run(self, session: RuntimeSession, run_id: str) -> Run:
        return session.get_run(run_id)

    def append_event(self, session: RuntimeSession, run_id: str, event_type: str, payload: dict[str, object]) -> RunEvent:
        run = session.get_run(run_id)
        event = RunEvent(event_id=uuid4().hex, event_type=event_type, payload=payload)
        run.add_event(event)
        return event

    def list_run_events(self, session: RuntimeSession, run_id: str) -> list[RunEvent]:
        return session.get_run(run_id).list_events()

    def validate_project_exists(self, project_id: str) -> None:
        self.store.get_project(project_id)

    def validate_session_exists(self, project_id: str, session_id: str) -> None:
        self.store.get_project(project_id).get_session(session_id)

    def validate_run_exists(self, session: RuntimeSession, run_id: str) -> None:
        session.get_run(run_id)

    def index_project(self, project_id: str) -> Project:
        """
        输入：
            project_id：要构建 RAG 索引的项目 ID。
        输出：
            Project：索引状态更新后的项目对象。
        作用：
            调用 RAG indexing 层构建项目级 RagIndex，并保存到 RuntimeStore。
        为什么需要这个函数：
            Runtime 是项目级索引对象的持有者；API 和 CLI 都应调用同一个入口，避免各自构建不同的 RAG 链路。
        """
        project = self.store.get_project(project_id)
        project.index_status = "indexing"  # type: ignore[assignment]
        try:
            index = build_project_index(project.project_id, project.repo_path, self.config)
            project.index = index
            project.index_status = "indexed"  # type: ignore[assignment]
        except Exception:
            project.index_status = "failed"  # type: ignore[assignment]
            project.index = None
            raise
        return project

    def get_project_index(self, project_id: str) -> RagIndex | None:
        """
        输入：
            project_id：项目 ID。
        输出：
            RagIndex 或 None：项目级 RAG 索引对象。
        作用：
            读取 RuntimeStore 中已构建的项目级 RagIndex。
        为什么需要这个函数：
            ask 执行前需要确认项目已索引，测试和后续 API 也需要能稳定查询索引是否存在。
        """
        project = self.store.get_project(project_id)
        return project.index

    def ask(self, project_id: str, session_id: str, question: str) -> Run:
        """
        输入：
            project_id：session 所属项目 ID。
            session_id：用户本轮问题所属的会话 ID。
            question：用户本轮问题。
        输出：
            Run：已经完成 graph 执行并更新状态的 run。
        作用：
            统一对外提供"提问并执行"的高层入口。
        为什么需要这个函数：
            ask 拿到完整归属路径后，可以在内部直接定位 project/session/run，不需要全局查找辅助函数。
        """
        project = self.store.get_project(project_id)
        session = project.get_session(session_id)
        run = self._run_graph(project, session_id, question)
        session.add_run(run)
        return run

    def _run_graph(self, project: Project, session_id: str, question: str) -> Run:
        """
        输入：
            project：run 所属 project。
            session：run 所属 session。
            run：要执行的 run。
        输出：
            Run：执行后更新状态和答案的 run。
        作用：
            把 run 转换成 graph state，调用 graph，并记录开始、内部和结束事件。
        为什么需要这个函数：
            graph 执行阶段已经持有完整 owner 链路，不需要再通过 ID 回查 project/session/run。
        """
        index = self.get_project_index(project.project_id)
        if index is None:
            raise RagIndexNotReadyError(f"rag index not ready: {project.project_id}")

        run = Run(
            run_id=uuid4().hex,
            session_id=session_id,
            question=question,
            status="running"
        )
        run.add_event(RunEvent(event_id=uuid4().hex, event_type="graph_start", payload={"run_id": run.run_id}))

        state = create_initial_state(
            project_id=project.project_id,
            repo_path=project.repo_path,
            question=run.question,
            rag_index=index,
            chat_model=self.chat_model,
            tool_executor=self.tool_executor,
        )
        result = self.graph.invoke(state)# result 是新的state

        for event in result.get("events", []):
            if isinstance(event, dict):
                run.add_event(RunEvent(event_id=uuid4().hex, event_type="graph_event", payload=event))

        run.status = str(result.get("status", "completed"))  # type: ignore[assignment]
        run.answer = str(result.get("answer", ""))
        run.reason = str(result.get("reason", ""))
        run.add_event(RunEvent(event_id=uuid4().hex, event_type="graph_finish", payload={"status": run.status}))
        return run
