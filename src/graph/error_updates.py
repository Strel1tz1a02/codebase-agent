from __future__ import annotations

from src.graph.state import AgentGraphState


def llm_error_update(
    state: AgentGraphState,
    stage: str,
    exc: Exception,
    **extra: object,
) -> AgentGraphState:
    error = str(exc) or exc.__class__.__name__
    return {
        "status": "failed",
        "reason": f"llm_error: {error}",
        **extra,
        "events": [
            *state.get("events", []),
            {"type": "llm_error", "stage": stage, "error": error},
        ],
    }
