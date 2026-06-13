from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.runs import RuntimeService


class FakeGraph:
    def invoke(self, state):
        return {
            "status": "completed",
            "answer": f"answer for {state['project_id']}",
            "events": [{"type": "answer_synthesized"}],
        }


def test_create_session_and_run_endpoints(tmp_path):
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(project_runtime=runtime)
    client = TestClient(app)

    session_response = client.post(
        "/sessions",
        json={"project_id": project.project_id},
    )
    session_id = session_response.json()["session_id"]
    run_response = client.post(
        f"/sessions/{session_id}/runs",
        json={"question": "Where is main?"},
    )

    assert session_response.status_code == 201
    assert session_response.json()["project_id"] == project.project_id
    assert run_response.status_code == 201
    assert run_response.json()["status"] == "completed"
    assert run_response.json()["answer"] == f"answer for {project.project_id}"


def test_get_run_and_events_endpoints(tmp_path):
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))
    session = runtime.create_session(project.project_id)
    run = runtime.ask(session.session_id, "Where is main?")
    app = create_app(project_runtime=runtime)
    client = TestClient(app)

    run_response = client.get(f"/sessions/{session.session_id}/runs/{run.run_id}")
    events_response = client.get(
        f"/sessions/{session.session_id}/runs/{run.run_id}/events"
    )

    assert run_response.status_code == 200
    assert run_response.json()["run_id"] == run.run_id
    assert events_response.status_code == 200
    assert [event["event_type"] for event in events_response.json()["events"]] == [
        "graph_start",
        "graph_event",
        "graph_finish",
    ]
