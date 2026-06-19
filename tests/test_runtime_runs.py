import pytest

from src.core.config import AppConfig, ModelConfig
from src.core.errors import RagIndexNotReadyError, RunNotFoundError, SessionNotFoundError
import src.runtime.service as runtime_service
from src.runtime.service import RuntimeService
from src.tools.history import READ_HISTORY_RUN_TOOL_NAME


def _write_repo_file(tmp_path):
    repo_file = tmp_path / "app.py"
    repo_file.write_text("def entrypoint():\n    return 'ok'\n", encoding="utf-8")


def test_runtime_ask_creates_run_for_session(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    assert project.sessions[session.session_id] is session
    assert session.runs[run.run_id] is run
    assert run.question == "Where is the entry point?"
    assert run.status == "completed"
    assert run.answer == ""


def test_runtime_records_run_events(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    event = runtime.append_event(session, run.run_id, "custom_event", {"ok": True})

    assert event.event_type == "custom_event"
    assert event.payload == {"ok": True}
    assert run.events[-1] is event
    assert runtime.list_run_events(project.project_id, session.session_id, run.run_id)[-1] is event


def test_runtime_reads_run_and_events_by_owner_ids(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    loaded = runtime.get_run(project.project_id, session.session_id, run.run_id)
    events = runtime.list_run_events(project.project_id, session.session_id, run.run_id)

    assert loaded is run
    assert [event.event_type for event in events] == [
        "graph_start",
        "graph_finish",
    ]


def test_runtime_validates_session_and_run_exist(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    runtime.validate_session_exists(project.project_id, session.session_id)
    runtime.validate_run_exists(session, run.run_id)

    with pytest.raises(SessionNotFoundError):
        runtime.validate_session_exists(project.project_id, "missing-session")
    with pytest.raises(RunNotFoundError):
        runtime.validate_run_exists(session, "missing-run")


def test_runtime_ask_runs_graph_and_records_start_and_finish_events(tmp_path):
    graph_calls = []

    class FakeGraph:
        def invoke(self, state):
            graph_calls.append(state)
            return {
                "status": "completed",
                "answer": "main is in src/main.py",
                "events": [{"type": "answer_synthesized"}],
            }

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    completed = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    assert completed.status == "completed"
    assert completed.answer == "main is in src/main.py"
    assert graph_calls[0]["project_id"] == project.project_id
    assert graph_calls[0]["repo_path"] == str(tmp_path)
    assert graph_calls[0]["messages"] == [
        {"role": "user", "content": "Where is the entry point?"}
    ]
    assert graph_calls[0]["rag_index"] is runtime.get_project_index(project.project_id)
    assert "retriever" not in graph_calls[0]
    assert [event.event_type for event in runtime.list_run_events(project.project_id, session.session_id, completed.run_id)] == [
        "graph_start",
        "graph_event",
        "graph_finish",
    ]


def test_runtime_injects_session_history_as_recent_history(tmp_path):
    graph_calls = []

    class FakeGraph:
        def invoke(self, state):
            graph_calls.append(state)
            return {
                "status": "completed",
                "answer": f"answer {len(graph_calls)}",
                "events": [],
            }

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    runtime.ask(project.project_id, session.session_id, "First question?")
    runtime.ask(project.project_id, session.session_id, "Second question?")

    assert graph_calls[0]["messages"] == [
        {"role": "user", "content": "First question?"}
    ]
    assert graph_calls[1]["messages"] == [
        {"role": "user", "content": "Second question?"}
    ]
    assert "user: First question?" in graph_calls[1]["recent_history"]
    assert "assistant: answer 1" in graph_calls[1]["recent_history"]
    assert "Second question?" not in graph_calls[1]["recent_history"]


def test_runtime_updates_and_injects_session_memory_summary(tmp_path):
    graph_calls = []

    class FakeSummaryResponse:
        content = "user name is L"

    class FakeChatModel:
        def invoke(self, prompt):
            return FakeSummaryResponse()

    class FakeGraph:
        def invoke(self, state):
            graph_calls.append(state)
            return {
                "status": "completed",
                "answer": "hello L" if len(graph_calls) == 1 else "your name is L",
                "events": [],
            }

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=FakeChatModel())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    runtime.ask(project.project_id, session.session_id, "my name is L")
    runtime.ask(project.project_id, session.session_id, "what is my name?")

    assert "user name is L" in session.memory_summary
    assert graph_calls[0]["memory_summary"] == ""
    assert "user name is L" in graph_calls[1]["memory_summary"]
    assert "user: my name is L" in graph_calls[1]["recent_history"]
    assert "what is my name?" not in graph_calls[1]["recent_history"]


def test_runtime_records_memory_summary_update_error(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "ok", "events": []}

    class FailingSummaryModel:
        def invoke(self, prompt):
            raise RuntimeError("quota exceeded")

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=FailingSummaryModel())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    run = runtime.ask(project.project_id, session.session_id, "remember this")

    assert session.memory_summary == ""
    assert run.events[-1].event_type == "memory_summary_failed"
    assert run.events[-1].payload == {"error": "quota exceeded"}


def test_runtime_injects_session_context_tool_executor(tmp_path):
    graph_calls = []

    class FakeGraph:
        def invoke(self, state):
            graph_calls.append(state)
            return {
                "status": "completed",
                "answer": f"answer {len(graph_calls)}",
                "events": [],
            }

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    first_run = runtime.ask(project.project_id, session.session_id, "First question?")
    runtime.ask(project.project_id, session.session_id, "Second question?")

    result = graph_calls[1]["tool_executor"](
        READ_HISTORY_RUN_TOOL_NAME,
        {"run_id": first_run.run_id},
    )

    assert result.ok is True
    assert result.output["session_id"] == session.session_id
    assert result.output["run_id"] == first_run.run_id
    assert result.output["question"] == "First question?"
    assert result.output["answer"] == "answer 1"


def test_runtime_injects_chat_model_into_graph_state(tmp_path):
    graph_calls = []
    chat_model = object()

    class FakeGraph:
        def invoke(self, state):
            graph_calls.append(state)
            return {"status": "completed", "answer": "ok", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=chat_model)
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    assert graph_calls[0]["chat_model"] is chat_model


def test_runtime_builds_chat_model_when_api_key_env_exists(monkeypatch):
    built_configs = []
    fake_model = object()

    def fake_build_chat_model(config):
        built_configs.append(config)
        return fake_model

    monkeypatch.setenv("TEST_LLM_KEY", "secret")
    monkeypatch.setattr(runtime_service, "build_chat_model", fake_build_chat_model)
    config = AppConfig(model_config=ModelConfig(api_key_env="TEST_LLM_KEY"))

    runtime = RuntimeService(graph=object(), config=config)

    assert runtime.chat_model is fake_model
    assert built_configs == [config]


def test_runtime_passes_app_config_when_indexing_project(monkeypatch, tmp_path):
    captured_calls = []
    fake_index = object()

    def fake_build_project_index(project_id, repo_path, config=None):
        captured_calls.append((project_id, repo_path, config))
        return fake_index

    monkeypatch.setattr(runtime_service, "build_project_index", fake_build_project_index)
    config = AppConfig()
    runtime = RuntimeService(graph=object(), config=config, chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))

    runtime.index_project(project.project_id)

    assert captured_calls == [(project.project_id, str(tmp_path), config)]
    assert project.index is fake_index


def test_runtime_ask_requires_indexed_project(tmp_path):
    runtime = RuntimeService(graph=object(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)

    with pytest.raises(RagIndexNotReadyError):
        runtime.ask(project.project_id, session.session_id, "Where is entrypoint?")


def test_runtime_get_methods_require_owner_scope(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph(), chat_model=object())
    project = runtime.create_project("demo", str(tmp_path))
    other_project = runtime.create_project("other", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    assert runtime.get_session(project.project_id, session.session_id) is session
    assert runtime.get_run(project.project_id, session.session_id, run.run_id) is run

    with pytest.raises(SessionNotFoundError):
        runtime.get_session(other_project.project_id, session.session_id)
    with pytest.raises(RunNotFoundError):
        other_session = runtime.create_session(other_project.project_id)
        runtime.get_run(other_project.project_id, other_session.session_id, run.run_id)


def test_runtime_uses_ask_as_public_run_entrypoint():
    runtime = RuntimeService(graph=object(), chat_model=object())

    assert hasattr(runtime, "ask")
    assert hasattr(runtime, "_run_graph")
