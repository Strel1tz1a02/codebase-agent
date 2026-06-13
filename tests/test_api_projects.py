from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.runs import RuntimeService


def test_create_project_endpoint(tmp_path):
    app = create_app(runtime=RuntimeService())
    client = TestClient(app)

    response = client.post(
        "/projects",
        json={"name": "demo", "repo_path": str(tmp_path)},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "demo"
    assert payload["repo_path"] == str(tmp_path)
    assert payload["index_status"] == "not_indexed"
    assert payload["project_id"]


def test_get_project_endpoint_returns_registered_project(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.get(f"/projects/{project.project_id}")

    assert response.status_code == 200
    assert response.json()["project_id"] == project.project_id


def test_index_project_endpoint_marks_project_indexed(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.post(f"/projects/{project.project_id}/index")

    assert response.status_code == 200
    assert response.json()["index_status"] == "indexed"
