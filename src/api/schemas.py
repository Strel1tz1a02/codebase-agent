from __future__ import annotations

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    repo_path: str


class CreateSessionResponse(BaseModel):
    session_id: str
    repo_path: str
    status: str
    message_count: int


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
