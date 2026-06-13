from __future__ import annotations

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    repo_path: str | None = None
    project_id: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    repo_path: str = ""
    project_id: str = ""
    status: str = "running"
    message_count: int = 0


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    session_id: str
    status: str
    question: str
    answer: str = ""
    reason: str = ""
    message_count: int


class SessionResponse(BaseModel):
    session_id: str
    repo_path: str
    status: str
    messages: list[dict[str, str]]
    trace: list[dict[str, object]]


class HealthResponse(BaseModel):
    status: str


class ToolListResponse(BaseModel):
    tools: list[str]


class CreateProjectRequest(BaseModel):
    name: str
    repo_path: str


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    repo_path: str
    index_status: str


class CreateRunRequest(BaseModel):
    question: str


class RunResponse(BaseModel):
    run_id: str
    session_id: str
    question: str
    status: str
    answer: str = ""
    reason: str = ""


class RunEventResponse(BaseModel):
    event_id: str
    run_id: str
    event_type: str
    payload: dict[str, object]


class RunEventListResponse(BaseModel):
    events: list[RunEventResponse]
