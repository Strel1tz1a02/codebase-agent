from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.errors import not_found_to_http_exception
from src.api.schemas import CreateRunRequest, RunEventListResponse, RunEventResponse, RunResponse
from src.core.errors import ProjectNotFoundError, RunNotFoundError, SessionNotFoundError
from src.runtime.events import RunEvent
from src.runtime.run import Run


def run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        question=run.question,
        status=run.status,
        answer=run.answer,
        reason=run.reason,
    )


def event_to_response(event: RunEvent) -> RunEventResponse:
    return RunEventResponse(
        event_id=event.event_id,
        event_type=event.event_type,
        payload=event.payload,
    )


def register_run_routes(app: FastAPI) -> None:
    @app.post(
        "/projects/{project_id}/sessions/{session_id}/runs",
        response_model=RunResponse,
        status_code=201,
    )
    def create_run(
        project_id: str,
        session_id: str,
        request: CreateRunRequest,
    ) -> RunResponse:
        try:
            run = app.state.runtime.ask(project_id, session_id, request.question)
        except (ProjectNotFoundError, SessionNotFoundError, RunNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return run_to_response(run)

    @app.get(
        "/projects/{project_id}/sessions/{session_id}/runs/{run_id}",
        response_model=RunResponse,
    )
    def get_run(project_id: str, session_id: str, run_id: str) -> RunResponse:
        try:
            session = app.state.runtime.store.get_project(project_id).get_session(session_id)
            run = session.get_run(run_id)
        except (ProjectNotFoundError, SessionNotFoundError, RunNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return run_to_response(run)

    @app.get(
        "/projects/{project_id}/sessions/{session_id}/runs/{run_id}/events",
        response_model=RunEventListResponse,
    )
    def list_run_events(
        project_id: str,
        session_id: str,
        run_id: str,
    ) -> RunEventListResponse:
        try:
            session = app.state.runtime.store.get_project(project_id).get_session(session_id)
            run = session.get_run(run_id)
            events = run.list_events()
        except (ProjectNotFoundError, SessionNotFoundError, RunNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return RunEventListResponse(events=[event_to_response(event) for event in events])
