from types import SimpleNamespace

from src.memory.prompts import build_memory_messages
from src.runtime.session import RuntimeSession


def test_build_memory_messages_includes_session_runs_only():
    session = RuntimeSession(session_id="session-1")
    session.runs["run-1"] = SimpleNamespace(
        question="First question?",
        answer="First answer.",
    )

    messages = build_memory_messages(session)

    assert messages == [
        {"role": "user", "content": "First question?"},
        {"role": "assistant", "content": "First answer."},
    ]
