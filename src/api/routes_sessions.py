from __future__ import annotations

from fastapi import FastAPI

from src.api.schemas import CreateSessionResponse
from src.runtime.sessions import RuntimeSession


def runtime_session_to_response(session: RuntimeSession) -> CreateSessionResponse:
    return CreateSessionResponse(
        session_id=session.session_id,
        project_id=session.project_id,
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
            session = app.state.runtime.create_session(project_id)
        except KeyError as exc:
            raise app.state.not_found_from_key_error(exc) from exc
        return runtime_session_to_response(session)

    @app.get(
        "/projects/{project_id}/sessions/{session_id}",
        response_model=CreateSessionResponse,
    )
    def get_session(project_id: str, session_id: str) -> CreateSessionResponse:
        try:
            session = app.state.runtime.get_session(project_id, session_id)
        except KeyError as exc:
            raise app.state.not_found_from_key_error(exc) from exc
        return runtime_session_to_response(session)
