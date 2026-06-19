from __future__ import annotations

from fastapi import FastAPI, Response, status

from src.api.errors import not_found_to_http_exception
from src.api.schemas import CreateSessionResponse, SessionListResponse
from src.core.errors import ProjectNotFoundError, SessionNotFoundError
from src.runtime.session import RuntimeSession

def runtime_session_to_response(session: RuntimeSession) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=session.session_id,
        status="running",
    )


def register_session_routes(app: FastAPI) -> None:
    @app.get(
        "/projects/{project_id}/sessions",
        response_model=SessionListResponse,
    )
    def list_sessions(project_id: str) -> SessionListResponse:
        try:
            sessions = app.state.runtime.list_sessions(project_id)
        except (ProjectNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return SessionListResponse(
            sessions=[runtime_session_to_response(session) for session in sessions]
        )

    @app.post(
        "/projects/{project_id}/sessions",
        response_model=CreateSessionResponse,
        status_code=201,
    )
    def create_session(project_id: str) -> CreateSessionResponse:
        try:
            session = app.state.runtime.create_session(project_id)
        except (ProjectNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return runtime_session_to_response(session)

    @app.get(
        "/projects/{project_id}/sessions/{session_id}",
        response_model=CreateSessionResponse,
    )
    def get_session(project_id: str, session_id: str) -> CreateSessionResponse:
        try:
            session = app.state.runtime.get_session(project_id, session_id)
        except (ProjectNotFoundError, SessionNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return runtime_session_to_response(session)

    @app.delete(
        "/projects/{project_id}/sessions/{session_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_session(project_id: str, session_id: str) -> Response:
        try:
            app.state.runtime.delete_session(project_id, session_id)
        except (ProjectNotFoundError, SessionNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return Response(status_code=status.HTTP_204_NO_CONTENT)
