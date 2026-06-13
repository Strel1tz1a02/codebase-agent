from __future__ import annotations

from fastapi import FastAPI, HTTPException, Response

from src.agent.adapter import next_decision
from src.api.routes_projects import register_project_routes
from src.api.routes_runs import register_run_routes
from src.api.routes_sessions import runtime_session_to_response
from src.api.schemas import (
    AskRequest,
    AskResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    HealthResponse,
    SessionResponse,
    ToolListResponse,
)
from src.runtime.graph_runner import build_graph_agent_runner
from src.runtime.runs import RuntimeService
from src.runtime.runtime import AgentRuntime
from src.runtime.session import Session
from src.tools.registry import TOOL_REGISTRY


def create_default_runtime() -> AgentRuntime:
    """
    输入：
        无。
    输出：
        AgentRuntime：接入默认 LangGraph runner 的 Runtime。
    作用：
        为模块级 FastAPI app 提供可直接运行的 AgentRuntime。
    设计原因：
        测试仍然可以通过 create_app(runtime=...) 注入 fake runtime；真实服务默认走现有 graph runner。
    """
    return AgentRuntime(
        agent_runner=build_graph_agent_runner(
            llm_decision_func=next_decision,
            max_steps=3,
        )
    )


def _not_found_from_key_error(exc: KeyError) -> HTTPException:
    """
    输入：
        exc：Runtime 或 Memory 抛出的 KeyError。
    输出：
        HTTPException：FastAPI 可识别的 404 异常。
    作用：
        把 Python 内部的缺失 session 错误转换成 HTTP 语义。
    设计原因：
        GET session 和 ask 都需要同样的 404 转换，集中处理可以避免格式不一致。
    """
    detail = str(exc.args[0]) if exc.args else "session not found"
    return HTTPException(status_code=404, detail=detail)


def _session_to_response(session: Session) -> SessionResponse:
    """
    输入：
        session：Runtime 内部保存的 Session 对象。
    输出：
        SessionResponse：可以直接返回给 HTTP 调用方的会话快照。
    作用：
        把内部 dataclass 转成 API 层稳定的响应 schema。
    设计原因：
        API 层不应该把内部 Message、Trace 对象直接暴露给外部调用方。
    """
    return SessionResponse(
        session_id=session.session_id,
        repo_path=session.repo_path,
        status=session.status,
        messages=session.message_dicts,
        trace=session.trace_dicts,
    )


def create_app(
    runtime: AgentRuntime | None = None,
    project_runtime: RuntimeService | None = None,
) -> FastAPI:
    """
    输入：
        runtime：可选的 AgentRuntime；测试可以传入 fake 或隔离的 runtime。
    输出：
        FastAPI：配置好路由的应用对象。
    作用：
        创建 V7 HTTP API，并把 HTTP 请求转交给 AgentRuntime。
    设计原因：
        create_app 让测试和真实 uvicorn 启动共享同一套路由定义。
    """
    app = FastAPI(title="codebase-agent API")
    app.state.runtime = runtime or create_default_runtime()
    app.state.project_runtime = project_runtime or RuntimeService()
    register_project_routes(app)
    register_run_routes(app)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """
        输入：
            无。
        输出：
            HealthResponse：服务可用状态。
        作用：
            给调用方提供最简单的存活检查。
        设计原因：
            API 服务需要一个不依赖 LLM 和仓库扫描的稳定健康检查入口。
        """
        return HealthResponse(status="ok")

    @app.get("/tools", response_model=ToolListResponse)
    def list_tools() -> ToolListResponse:
        """
        输入：
            无。
        输出：
            ToolListResponse：当前注册的工具名称列表。
        作用：
            让外部调用方知道 Agent 当前可用哪些工具。
        设计原因：
            V7 第一版只需要暴露工具名，后续再升级为完整工具协议。
        """
        return ToolListResponse(tools=list(TOOL_REGISTRY.keys()))

    @app.post("/sessions")
    def create_session(
        request: CreateSessionRequest,
        response: Response,
    ) -> dict[str, object] | CreateSessionResponse:
        """
        输入：
            request：包含 repo_path 的创建会话请求。
        输出：
            CreateSessionResponse：新 session 的基本状态。
        作用：
            创建一个绑定仓库路径的 Agent 会话。
        设计原因：
            HTTP 调用方需要先拿到 session_id，后续才能围绕同一仓库继续交互。
        """
        if request.project_id:
            try:
                session = app.state.project_runtime.create_session(request.project_id)
            except KeyError as exc:
                raise _not_found_from_key_error(exc) from exc
            response.status_code = 201
            return runtime_session_to_response(session)

        if not request.repo_path:
            raise HTTPException(status_code=422, detail="repo_path or project_id is required")

        session = app.state.runtime.create_session(request.repo_path)
        return CreateSessionResponse(
            session_id=session.session_id,
            repo_path=session.repo_path,
            status=session.status,
            message_count=len(session.messages),
        )

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str) -> SessionResponse | dict[str, object]:
        """
        输入：
            session_id：要查询的会话 ID。
        输出：
            SessionResponse：会话状态、消息历史和 trace 摘要。
        作用：
            让 HTTP 调用方查看指定 session 的当前状态。
        设计原因：
            Runtime 的 KeyError 属于 Python 内部异常，API 层需要转换成 HTTP 404。
        """
        try:
            session = app.state.runtime.memory.get_session(session_id)
        except KeyError as exc:
            try:
                runtime_session = app.state.project_runtime.get_session(session_id)
            except KeyError:
                raise _not_found_from_key_error(exc) from exc
            return runtime_session_to_response(runtime_session)
        return _session_to_response(session)

    @app.post("/sessions/{session_id}/ask", response_model=AskResponse)
    def ask_session(session_id: str, request: AskRequest) -> AskResponse:
        """
        输入：
            session_id：已有会话 ID。
            request：包含 question 的提问请求。
        输出：
            AskResponse：本轮 Agent 运行状态、回答、原因和消息数量。
        作用：
            把 HTTP 提问请求转交给 AgentRuntime.ask。
        设计原因：
            API 层只负责 HTTP 适配，多轮状态和 runner 调用仍由 Runtime 管理。
        """
        try:
            result = app.state.runtime.ask(session_id, request.question)
        except KeyError as exc:
            raise _not_found_from_key_error(exc) from exc

        return AskResponse(
            session_id=str(result["session_id"]),
            status=str(result["status"]),
            question=str(result["question"]),
            answer=str(result.get("answer", "")),
            reason=str(result.get("reason", "")),
            message_count=int(result["message_count"]),
        )

    return app


app = create_app()
