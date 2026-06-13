import json

from src.cli.main import main
from src.runtime.runs import RuntimeService


class FakeGraph:
    def invoke(self, state):
        return {
            "status": "completed",
            "answer": f"answer for {state['project_id']}",
            "events": [],
        }


def test_cli_index_creates_project(tmp_path, capsys):
    runtime = RuntimeService()

    exit_code = main(
        ["index", "--repo", str(tmp_path), "--project", "demo"],
        runtime=runtime,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["name"] == "demo"
    assert payload["repo_path"] == str(tmp_path)
    assert payload["index_status"] == "indexed"


def test_cli_ask_runs_project_question(tmp_path, capsys):
    runtime = RuntimeService(graph=FakeGraph())
    project = runtime.create_project("demo", str(tmp_path))

    exit_code = main(
        ["ask", "--project", project.project_id, "Where is main?"],
        runtime=runtime,
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "completed"
    assert payload["answer"] == f"answer for {project.project_id}"


def test_cli_serve_starts_uvicorn(monkeypatch):
    calls = []

    def fake_run(app_path, host, port):
        calls.append({"app_path": app_path, "host": host, "port": port})

    monkeypatch.setattr("src.cli.main.uvicorn.run", fake_run)

    exit_code = main(["serve", "--host", "127.0.0.1", "--port", "8001"])

    assert exit_code == 0
    assert calls == [
        {
            "app_path": "src.api.app:app",
            "host": "127.0.0.1",
            "port": 8001,
        }
    ]
