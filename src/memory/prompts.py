from __future__ import annotations

from src.runtime.session import RuntimeSession


def build_memory_messages(session: RuntimeSession) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for run in session.runs.values():
        if run.question:
            messages.append({"role": "user", "content": run.question})
        if run.answer:
            messages.append({"role": "assistant", "content": run.answer})
    return messages


def format_memory_summary(session: RuntimeSession) -> str:
    return session.memory_summary.strip() or "无"


def format_recent_history(session: RuntimeSession, limit_runs: int = 3) -> str:
    recent_runs = list(session.runs.values())[-max(0, limit_runs):]
    lines: list[str] = []
    for run in recent_runs:
        if run.question:
            lines.append(f"user: {run.question}")
        if run.answer:
            lines.append(f"assistant: {run.answer}")
    return "\n".join(lines) if lines else "无"
