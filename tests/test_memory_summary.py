from types import SimpleNamespace

from src.memory.prompts import format_recent_history
from src.memory.summary import append_memory_summary, summarize_latest_run, update_memory_summary
from src.runtime.session import RuntimeSession


class FakeSummaryResponse:
    def __init__(self, content: str):
        self.content = content


class RecordingSummaryModel:
    def __init__(self, content: str):
        self.content = content
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        return FakeSummaryResponse(self.content)


def test_format_recent_history_limits_by_run_without_splitting_pairs():
    session = RuntimeSession(session_id="session-1")
    session.runs["run-1"] = SimpleNamespace(question="first question", answer="first answer")
    session.runs["run-2"] = SimpleNamespace(question="second question", answer="second answer")

    text = format_recent_history(session, limit_runs=1)

    assert "user: first question" not in text
    assert "assistant: first answer" not in text
    assert "user: second question" in text
    assert "assistant: second answer" in text


def test_summarize_latest_run_tags_summary_with_latest_run_id():
    session = RuntimeSession(session_id="session-1")
    session.runs["run-1"] = SimpleNamespace(run_id="run-1", question="old question", answer="old answer")
    session.runs["run-2"] = SimpleNamespace(run_id="run-2", question="my name is L", answer="hello L")
    model = RecordingSummaryModel("user said their name is L.")

    summary = summarize_latest_run(session, model)

    assert summary == "[run_id=run-2]\nuser said their name is L."
    assert len(model.prompts) == 1
    assert "my name is L" in model.prompts[0]
    assert "hello L" in model.prompts[0]
    assert "old question" not in model.prompts[0]


def test_update_memory_summary_appends_new_llm_summary():
    session = RuntimeSession(session_id="session-1", memory_summary="existing summary.")
    session.runs["run-1"] = SimpleNamespace(run_id="run-1", question="my name is L", answer="hello L")
    model = RecordingSummaryModel("user said their name is L.")

    summary = update_memory_summary(session, model)

    assert summary == "existing summary.\n\n[run_id=run-1]\nuser said their name is L."


def test_append_memory_summary_ignores_empty_new_summary():
    assert append_memory_summary("existing summary.", "   ") == "existing summary."
