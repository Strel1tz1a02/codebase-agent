from types import SimpleNamespace

from src.runtime.memory import build_memory_messages
from src.runtime.session import RuntimeSession


def test_build_memory_messages_includes_history_and_current_question():
    """Verify memory builds history and current question in message order."""
    session = RuntimeSession(session_id="session-1")
    session.runs["run-1"] = SimpleNamespace(
        question="First question?",
        answer="First answer.",
    )

    messages = build_memory_messages(session, "Second question?")

    assert messages == [
        {"role": "user", "content": "First question?"},
        {"role": "assistant", "content": "First answer."},
        {"role": "user", "content": "Second question?"},
    ]

