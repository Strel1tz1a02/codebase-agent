from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class CreateProjectRequest(BaseModel):
    name: str
    repo_path: str


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    repo_path: str
    index_status: str


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str = "running"


class CreateRunRequest(BaseModel):
    question: str


class RunResponse(BaseModel):
    run_id: str
    question: str
    status: str
    answer: str = ""
    reason: str = ""


class RunEventResponse(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, object]


class RunEventListResponse(BaseModel):
    events: list[RunEventResponse]
