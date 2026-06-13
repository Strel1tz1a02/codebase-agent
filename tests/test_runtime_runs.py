import pytest

from src.runtime.runs import RuntimeService


def test_runtime_creates_run_for_session(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)

    run = runtime.create_run(session.session_id, "Where is the entry point?")

    assert run.session_id == session.session_id
    assert run.question == "Where is the entry point?"
    assert run.status == "queued"
    assert run.answer == ""


def test_runtime_records_run_events(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)
    run = runtime.create_run(session.session_id, "Where is the entry point?")

    event = runtime.append_event(run.run_id, "custom_event", {"ok": True})

    assert event.run_id == run.run_id
    assert event.event_type == "custom_event"
    assert event.payload == {"ok": True}
    assert runtime.list_run_events(run.run_id) == [event]


def test_runtime_validates_session_and_run_exist(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)
    run = runtime.create_run(session.session_id, "Where is the entry point?")

    runtime.validate_session_exists(session.session_id)
    runtime.validate_run_exists(run.run_id)

    with pytest.raises(KeyError):
        runtime.validate_session_exists("missing-session")
    with pytest.raises(KeyError):
        runtime.validate_run_exists("missing-run")


def test_runtime_runs_graph_and_records_start_and_finish_events(tmp_path):
    graph_calls = []

    class FakeGraph:
        def invoke(self, state):
            graph_calls.append(state)
            return {
                "status": "completed",
                "answer": "main is in src/main.py",
                "events": [{"type": "answer_synthesized"}],
            }

    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)
    run = runtime.create_run(session.session_id, "Where is the entry point?")

    completed = runtime.run_graph(run.run_id)

    assert completed is run
    assert completed.status == "completed"
    assert completed.answer == "main is in src/main.py"
    assert graph_calls[0]["project_id"] == project.project_id
    assert graph_calls[0]["repo_path"] == str(tmp_path)
    assert graph_calls[0]["messages"] == [
        {"role": "user", "content": "Where is the entry point?"}
    ]
    assert [event.event_type for event in runtime.list_run_events(run.run_id)] == [
        "graph_start",
        "graph_event",
        "graph_finish",
    ]
