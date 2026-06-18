from __future__ import annotations

from fastapi import FastAPI
from uuid import uuid4

from src.api.errors import not_found_to_http_exception
from src.api.schemas import CreateSessionResponse
from src.core.errors import ProjectNotFoundError, SessionNotFoundError
from src.runtime.session import RuntimeSession

def runtime_session_to_response(session: RuntimeSession) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=session.session_id,
        status="running",
    )


def register_session_routes(app: FastAPI) -> None:
    @app.post(
        "/projects/{project_id}/sessions",
        response_model=CreateSessionResponse,
        status_code=201,
    )
    def create_session(project_id: str) -> CreateSessionResponse:
        try:
            session = RuntimeSession(session_id=uuid4().hex)
            app.state.runtime.store.get_project(project_id).add_session(session)
        except (ProjectNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return runtime_session_to_response(session)

    @app.get(
        "/projects/{project_id}/sessions/{session_id}",
        response_model=CreateSessionResponse,
    )
    def get_session(project_id: str, session_id: str) -> CreateSessionResponse:
        try:
            session = app.state.runtime.store.get_project(project_id).get_session(session_id)
        except (ProjectNotFoundError, SessionNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return runtime_session_to_response(session)
