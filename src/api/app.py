from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes_projects import register_project_routes
from src.api.routes_runs import register_run_routes
from src.api.routes_sessions import register_session_routes
from src.api.schemas import HealthResponse
from src.runtime.runs import RuntimeService


def create_app(runtime: RuntimeService | None = None) -> FastAPI:
    """
    输入：
        runtime：可选的 RuntimeService；测试可以传入 fake graph 或隔离的 runtime。
    输出：
        FastAPI：配置好路由的应用对象。
    作用：
        创建只使用新 RuntimeService 的 HTTP API。
    设计原因：
        API 层不再同时维护 AgentRuntime 和 RuntimeService 两套状态，所有 project/session/run
        生命周期都从同一个 runtime.store 出发。
    """
    app = FastAPI(title="codebase-agent API")
    app.state.runtime = runtime or RuntimeService()
    register_project_routes(app)
    register_session_routes(app)
    register_run_routes(app)
    ui_dir = Path(__file__).resolve().parents[1] / "ui" / "static"
    app.mount("/ui/static", StaticFiles(directory=ui_dir), name="ui-static")

    @app.get("/ui", include_in_schema=False)
    def ui() -> FileResponse:
        return FileResponse(ui_dir / "index.html")

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

    return app


app = create_app()
