from __future__ import annotations

from src.runtime.sessions import RuntimeSession


def runtime_session_to_response(session: RuntimeSession) -> dict[str, str]:
    return {
        "session_id": session.session_id,
        "project_id": session.project_id,
        "status": "running",
    }
