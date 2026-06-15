import pytest

from src.core.config import AppConfig, ModelConfig
from src.core.errors import RagIndexNotReadyError
import src.runtime.runs as runtime_runs
from src.runtime.runs import RuntimeService


def _write_repo_file(tmp_path):
    repo_file = tmp_path / "app.py"
    repo_file.write_text("def entrypoint():\n    return 'ok'\n", encoding="utf-8")


def test_runtime_ask_creates_run_for_session(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)

    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    assert project.sessions[session.session_id] is session
    assert session.runs[run.run_id] is run
    assert run.session_id == session.session_id
    assert run.question == "Where is the entry point?"
    assert run.status == "completed"
    assert run.answer == ""


def test_runtime_records_run_events(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    event = runtime.append_event(session, run.run_id, "custom_event", {"ok": True})

    assert event.run_id == run.run_id
    assert event.event_type == "custom_event"
    assert event.payload == {"ok": True}
    assert run.events[-1] is event
    assert runtime.list_run_events(session, run.run_id)[-1] is event


def test_runtime_validates_session_and_run_exist(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    runtime.validate_session_exists(project.project_id, session.session_id)
    runtime.validate_run_exists(session, run.run_id)

    with pytest.raises(KeyError):
        runtime.validate_session_exists(project.project_id, "missing-session")
    with pytest.raises(KeyError):
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
    runtime = RuntimeService(graph=FakeGraph())
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
    assert [event.event_type for event in runtime.list_run_events(session, completed.run_id)] == [
        "graph_start",
        "graph_event",
        "graph_finish",
    ]


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
    monkeypatch.setattr(runtime_runs, "build_chat_model", fake_build_chat_model)
    config = AppConfig(model=ModelConfig(api_key_env="TEST_LLM_KEY"))

    runtime = RuntimeService(graph=object(), config=config)

    assert runtime.chat_model is fake_model
    assert built_configs == [config.model]


def test_runtime_ask_requires_indexed_project(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)

    with pytest.raises(RagIndexNotReadyError):
        runtime.ask(project.project_id, session.session_id, "Where is entrypoint?")


def test_runtime_get_methods_require_owner_scope(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return {"status": "completed", "answer": "", "events": []}

    _write_repo_file(tmp_path)
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    other_project = runtime.create_project("other", str(tmp_path))
    runtime.index_project(project.project_id)
    session = runtime.create_session(project.project_id)
    run = runtime.ask(project.project_id, session.session_id, "Where is the entry point?")

    assert runtime.get_session(project.project_id, session.session_id) is session
    assert runtime.get_run(session, run.run_id) is run

    with pytest.raises(KeyError):
        runtime.get_session(other_project.project_id, session.session_id)
    with pytest.raises(KeyError):
        runtime.get_run(runtime.create_session(other_project.project_id), run.run_id)


def test_runtime_uses_ask_as_public_run_entrypoint():
    runtime = RuntimeService(graph=object())

    assert hasattr(runtime, "ask")
    assert not hasattr(runtime, "create_run")
    assert not hasattr(runtime, "run_graph")
    assert hasattr(runtime, "_create_run")
    assert hasattr(runtime, "_run_graph")
    assert not hasattr(runtime, "_find_session")
    assert not hasattr(runtime, "_find_run")
