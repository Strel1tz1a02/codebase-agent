from __future__ import annotations

from fastapi import FastAPI, HTTPException

from src.api.schemas import CreateRunRequest, RunEventListResponse, RunEventResponse, RunResponse
from src.runtime.events import RunEvent
from src.runtime.runs import Run


def run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        session_id=run.session_id,
        question=run.question,
        status=run.status,
        answer=run.answer,
        reason=run.reason,
    )


def event_to_response(event: RunEvent) -> RunEventResponse:
    return RunEventResponse(
        event_id=event.event_id,
        run_id=event.run_id,
        event_type=event.event_type,
        payload=event.payload,
    )


def register_run_routes(app: FastAPI) -> None:
    @app.post("/sessions/{session_id}/runs", response_model=RunResponse, status_code=201)
    def create_run(session_id: str, request: CreateRunRequest) -> RunResponse:
        try:
            run = app.state.project_runtime.ask(session_id, request.question)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return run_to_response(run)

    @app.get("/sessions/{session_id}/runs/{run_id}", response_model=RunResponse)
    def get_run(session_id: str, run_id: str) -> RunResponse:
        try:
            run = app.state.project_runtime.get_run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if run.session_id != session_id:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return run_to_response(run)

    @app.get(
        "/sessions/{session_id}/runs/{run_id}/events",
        response_model=RunEventListResponse,
    )
    def list_run_events(session_id: str, run_id: str) -> RunEventListResponse:
        try:
            run = app.state.project_runtime.get_run(run_id)
            events = app.state.project_runtime.list_run_events(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        if run.session_id != session_id:
            raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
        return RunEventListResponse(events=[event_to_response(event) for event in events])
