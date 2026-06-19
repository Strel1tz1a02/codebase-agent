from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.runtime.session import RuntimeSession


READ_HISTORY_RUN_TOOL_NAME = "read_history_run"


class ReadHistoryRunInput(BaseModel):
    run_id: str = Field(
        default="",
        description="Run id from memory_summary, for example the id in [run_id=...].",
    )


def read_history_run_placeholder(run_id: str) -> dict[str, object]:
    raise ValueError("read_history_run requires the current session runtime context")


def read_history_run(session: RuntimeSession, run_id: str) -> dict[str, object]:
    run_id = run_id.strip()
    if not run_id:
        raise ValueError("run_id is required")

    run = session.get_run(run_id)
    return {
        "session_id": session.session_id,
        "run_id": run.run_id,
        "question": run.question,
        "answer": run.answer,
        "status": run.status,
        "reason": run.reason,
    }


read_history_run_tool = StructuredTool.from_function(
    func=read_history_run_placeholder,
    name=READ_HISTORY_RUN_TOOL_NAME,
    description=(
        "Read the full question and answer for one previous run in the current session. "
        "Use this when memory_summary mentions a [run_id=...] entry and the complete historical "
        "conversation is needed. Argument: run_id must come from the current session memory summary."
    ),
    args_schema=ReadHistoryRunInput,
)
