from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.errors import not_found_to_http_exception
from src.api.schemas import CreateRunRequest, RunEventListResponse, RunEventResponse, RunListResponse, RunResponse
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
    @app.get(
        "/projects/{project_id}/sessions/{session_id}/runs",
        response_model=RunListResponse,
    )
    def list_runs(project_id: str, session_id: str) -> RunListResponse:
        try:
            runs = app.state.runtime.list_runs(project_id, session_id)
        except (ProjectNotFoundError, SessionNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return RunListResponse(runs=[run_to_response(run) for run in runs])

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
            run = app.state.runtime.get_run(project_id, session_id, run_id)
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
            events = app.state.runtime.list_run_events(project_id, session_id, run_id)
        except (ProjectNotFoundError, SessionNotFoundError, RunNotFoundError, KeyError) as exc:
            raise not_found_to_http_exception(exc) from exc
        return RunEventListResponse(events=[event_to_response(event) for event in events])
