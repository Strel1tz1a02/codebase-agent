from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from src.core.errors import ProjectNotFoundError, RagIndexNotReadyError
from src.graph.builder import build_graph
from src.graph.state import create_initial_state
from src.rag.indexing import build_project_index
from src.rag.schemas import RagIndex
from src.runtime.events import RunEvent
from src.runtime.projects import Project
from src.runtime.sessions import RuntimeSession
from src.runtime.store import RuntimeStore


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
        RuntimeService 只维护 graph 和 store；project/session/run 的读取必须沿所有权路径进行，
        避免重新退回全局平铺索引或全局遍历查找。
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
            session 和 run 都归属于 project；先注册 project 可以让后续流程使用稳定 project_id。
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
            从 store 根入口读取已注册项目。
        为什么需要这个函数：
            project 是运行时对象所有权的根，后续 session/run 查询都应先明确 project。
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
        project = self.get_project(project_id)
        project.index_status = "indexing"  # type: ignore[assignment]
        try:
            index = build_project_index(project.project_id, project.repo_path)
            self.store.project_indexes[project.project_id] = index
            project.index_status = "indexed"  # type: ignore[assignment]
        except Exception:
            project.index_status = "failed"  # type: ignore[assignment]
            self.store.project_indexes.pop(project.project_id, None)
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
        self.validate_project_exists(project_id)
        return self.store.project_indexes.get(project_id)

    def create_session(self, project_id: str) -> RuntimeSession:
        """
        输入：
            project_id：要绑定的项目 ID。
        输出：
            RuntimeSession：新创建的会话对象。
        作用：
            创建一个归属于指定 project 的对话容器。
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

    def get_session(self, project_id: str, session_id: str) -> RuntimeSession:
        """
        输入：
            project_id：session 所属项目 ID。
            session_id：会话 ID。
        输出：
            RuntimeSession：对应会话对象。
        作用：
            从指定 project 的 sessions 中读取 session。
        为什么需要这个函数：
            session 查询应显式指定归属 project，避免为了便利引入全局遍历查找。
        """
        project = self.get_project(project_id)
        session = project.sessions.get(session_id)
        if not isinstance(session, RuntimeSession):
            raise KeyError(f"session not found: {session_id}")
        return session

    def validate_session_exists(self, project_id: str, session_id: str) -> None:
        """
        输入：
            project_id：session 所属项目 ID。
            session_id：会话 ID。
        输出：
            None；session 不存在时抛出 KeyError。
        作用：
            明确校验 session_id 是否存在于指定 project 下。
        为什么需要这个函数：
            校验也应沿 project -> sessions 所有权路径完成，而不是只按全局 session_id 判断。
        """
        self.get_session(project_id, session_id)

    def ask(self, project_id: str, session_id: str, question: str) -> Run:
        """
        输入：
            project_id：session 所属项目 ID。
            session_id：用户本轮问题所属的会话 ID。
            question：用户本轮问题。
        输出：
            Run：已经完成 graph 执行并更新状态的 run。
        作用：
            统一对外提供“提问并执行”的高层入口。
        为什么需要这个函数：
            ask 拿到完整归属路径后，可以在内部直接定位 project/session/run，不需要全局查找辅助函数。
        """
        project = self.get_project(project_id)
        session = self.get_session(project_id, session_id)
        run = self._create_run(session, question)
        return self._run_graph(project, session, run)

    def _create_run(self, session: RuntimeSession, question: str) -> Run:
        """
        输入：
            session：run 所属会话对象。
            question：用户本轮问题。
        输出：
            Run：新创建且状态为 queued 的 run。
        作用：
            为一次用户提问创建可追踪执行记录。
        为什么需要这个函数：
            创建 run 时已经持有 owner session，直接写入 session.runs 可以保持所有权关系明确。
        """
        run = Run(
            run_id=uuid4().hex,
            session_id=session.session_id,
            question=question,
        )
        session.runs[run.run_id] = run
        return run

    def get_run(self, session: RuntimeSession, run_id: str) -> Run:
        """
        输入：
            session：run 所属会话对象。
            run_id：run ID。
        输出：
            Run：对应 run 对象。
        作用：
            从指定 session 的 runs 中读取 run。
        为什么需要这个函数：
            run 查询必须指定 owner session，避免相同 run_id 或错误归属导致跨 session 读取。
        """
        run = session.runs.get(run_id)
        if not isinstance(run, Run):
            raise KeyError(f"run not found: {run_id}")
        return run

    def validate_run_exists(self, session: RuntimeSession, run_id: str) -> None:
        """
        输入：
            session：run 所属会话对象。
            run_id：run ID。
        输出：
            None；run 不存在时抛出 KeyError。
        作用：
            明确校验 run_id 是否存在于指定 session 下。
        为什么需要这个函数：
            校验也应沿 session -> runs 所有权路径完成，而不是全局扫所有 run。
        """
        self.get_run(session, run_id)

    def append_event(
        self,
        session: RuntimeSession,
        run_id: str,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> RunEvent:
        """
        输入：
            session：事件所属 run 的 owner session。
            run_id：事件所属 run。
            event_type：事件类型。
            payload：事件详情。
        输出：
            RunEvent：新追加的事件对象。
        作用：
            给某次 run 追加一条结构化事件。
        为什么需要这个函数：
            事件写入也必须先指定 session 归属，避免只凭 run_id 跨 session 写入。
        """
        run = self.get_run(session, run_id)
        event = RunEvent(
            event_id=uuid4().hex,
            run_id=run_id,
            event_type=event_type,
            payload=dict(payload or {}),
        )
        run.events.append(event)
        return event

    def list_run_events(self, session: RuntimeSession, run_id: str) -> list[RunEvent]:
        """
        输入：
            session：run 所属会话对象。
            run_id：run ID。
        输出：
            list[RunEvent]：该 run 的事件快照。
        作用：
            查询一次 run 的执行轨迹。
        为什么需要这个函数：
            事件读取应从指定 session 下的 run 开始，保持 project owns session owns run owns event 的模型。
        """
        run = self.get_run(session, run_id)
        return list(run.events)

    def _run_graph(self, project: Project, session: RuntimeSession, run: Run) -> Run:
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

        run.status = "running"
        self.append_event(session, run.run_id, "graph_start", {"run_id": run.run_id})

        state = create_initial_state(
            project_id=project.project_id,
            repo_path=project.repo_path,
            question=run.question,
        )
        state["rag_index"] = index
        result = self.graph.invoke(state)  # type: ignore[attr-defined]

        for event in result.get("events", []):
            if isinstance(event, dict):
                self.append_event(session, run.run_id, "graph_event", event)

        run.status = str(result.get("status", "completed"))  # type: ignore[assignment]
        run.answer = str(result.get("answer", ""))
        run.reason = str(result.get("reason", ""))
        self.append_event(session, run.run_id, "graph_finish", {"status": run.status})
        return run
