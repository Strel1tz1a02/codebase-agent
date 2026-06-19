from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from src.core.config import AppConfig
from src.core.errors import RagIndexNotReadyError
from src.graph.builder import build_graph
from src.graph.state import create_initial_state
from src.memory.prompts import format_recent_history
from src.memory.summary import update_memory_summary
from src.models.chat import build_chat_model
from src.rag.indexing import build_project_index
from src.rag.schemas import RagIndex
from src.runtime.events import RunEvent
from src.runtime.run import Run
from src.runtime.session import RuntimeSession
from src.runtime.store import RuntimeStore
from src.tools.toolkit import ToolContext, execute_tool

if TYPE_CHECKING:
    from src.runtime.project import Project


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
        tool_executor: callable | None = None,
        store_path: str | Path | None = None,
    ) -> None:
        self.graph = graph or build_graph()
        self.config = config or AppConfig()
        self.chat_model = chat_model or build_chat_model(self.config)
        self.tool_executor = tool_executor or execute_tool
        self.store = RuntimeStore.load(store_path) if store_path is not None else RuntimeStore()

    def create_project(self, project_name: str, repo_path: str) -> Project:
        """创建项目并写入 RuntimeStore。"""
        from src.runtime.project import Project

        project = Project(project_id=uuid4().hex, name=project_name, repo_path=repo_path)
        self.store.add_project(project)
        return project

    def get_project(self, project_id: str) -> Project:
        """按 project_id 读取项目。"""
        return self.store.get_project(project_id)

    def list_projects(self) -> list[Project]:
        """列出当前 Runtime 管理的所有项目。"""
        return self.store.list_projects()

    def delete_project(self, project_id: str) -> Project:
        """删除指定项目，并返回被删除的项目对象。"""
        return self.store.delete_project(project_id)

    def create_session(self, project_id: str) -> RuntimeSession:
        """为指定 project 创建新的运行会话。"""
        session = RuntimeSession(session_id=uuid4().hex)
        self.store.get_project(project_id).add_session(session)
        self.store.save()
        return session

    def get_session(self, project_id: str, session_id: str) -> RuntimeSession:
        """按 project_id 和 session_id 读取会话。"""
        return self.store.get_project(project_id).get_session(session_id)

    def list_sessions(self, project_id: str) -> list[RuntimeSession]:
        """返回指定 project 下的所有会话，供 API 和前端恢复侧栏导航。"""
        return list(self.store.get_project(project_id).sessions.values())

    def delete_session(self, project_id: str, session_id: str) -> RuntimeSession:
        """删除指定 project 下的会话，并同步保存 RuntimeStore。"""
        project = self.store.get_project(project_id)
        session = project.get_session(session_id)
        del project.sessions[session_id]# 从字典中删除指定的键值对
        self.store.save()
        return session

    def get_run(self, project_id: str, session_id: str, run_id: str) -> Run:
        """按 project/session/run 归属路径读取 run，供 API 边界调用。"""
        return self.get_session(project_id, session_id).get_run(run_id)

    def list_runs(self, project_id: str, session_id: str) -> list[Run]:
        """返回指定 session 下的所有 run，供前端恢复会话历史。"""
        return list(self.get_session(project_id, session_id).runs.values())

    def append_event(self, session: RuntimeSession, run_id: str, event_type: str, payload: dict[str, object]) -> RunEvent:
        """为指定 run 追加运行事件。"""
        run = session.get_run(run_id)
        event = RunEvent(event_id=uuid4().hex, event_type=event_type, payload=payload)
        run.add_event(event)
        self.store.save()
        return event

    def list_run_events(self, project_id: str, session_id: str, run_id: str) -> list[RunEvent]:
        """按 project/session/run 归属路径返回 run 的事件列表。"""
        return self.get_run(project_id, session_id, run_id).list_events()

    def validate_project_exists(self, project_id: str) -> None:
        """校验 project 是否存在，不存在时抛出领域异常。"""
        self.store.get_project(project_id)

    def validate_session_exists(self, project_id: str, session_id: str) -> None:
        """校验 session 是否存在，不存在时抛出领域异常。"""
        self.store.get_project(project_id).get_session(session_id)

    def validate_run_exists(self, session: RuntimeSession, run_id: str) -> None:
        """校验 run 是否存在，不存在时抛出领域异常。"""
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
        self.store.save()
        try:
            index = build_project_index(project.project_id, project.repo_path, self.config)
            project.index = index
            project.index_status = "indexed"  # type: ignore[assignment]
            self.store.save()
        except Exception:
            project.index_status = "failed"  # type: ignore[assignment]
            project.index = None
            self.store.save()
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
        run = self._run_graph(project, session, question)
        session.add_run(run)
        memory_update = update_memory_summary(session, self.chat_model)
        session.memory_summary = memory_update.summary
        if memory_update.error:
            run.add_event(
                RunEvent(
                    event_id=uuid4().hex,
                    event_type="memory_summary_failed",
                    payload={"error": memory_update.error},
                )
            )
        self.store.save()
        return run

    def _run_graph(self, project: Project, session: RuntimeSession, question: str) -> Run:
        """
        输入：
            project：run 所属 project。
            session：run 所属 session。
            question：用户本轮问题。
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
            question=question,
            status="running",
        )
        run.add_event(RunEvent(event_id=uuid4().hex, event_type="graph_start", payload={"run_id": run.run_id}))

        state = create_initial_state(
            project_id=project.project_id,
            repo_path=project.repo_path,
            question=run.question,
            rag_index=index,
            chat_model=self.chat_model,
            tool_executor=lambda tool_name, arguments: self.tool_executor(
                tool_name,
                arguments,
                context=ToolContext(
                    session=session,
                    project=project,
                    repo_path=project.repo_path,
                ),
            ),# graph层不参与给context参数，所以graph层仍然是2参数版本的executor，context 在run层喂进去
            memory_summary=session.memory_summary,
            recent_history=format_recent_history(session),
        )
        result = self.graph.invoke(state)

        for event in result.get("events", []):
            if isinstance(event, dict):
                run.add_event(RunEvent(event_id=uuid4().hex, event_type="graph_event", payload=event))

        run.status = str(result.get("status", "completed"))  # type: ignore[assignment]
        run.answer = str(result.get("answer", ""))
        run.reason = str(result.get("reason", ""))
        run.add_event(RunEvent(event_id=uuid4().hex, event_type="graph_finish", payload={"status": run.status}))
        return run
