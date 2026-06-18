from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.service import RuntimeService


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


def test_list_projects_endpoint_returns_registered_projects(tmp_path):
    runtime = RuntimeService()
    first = runtime.create_project("first", str(tmp_path / "first"))
    second = runtime.create_project("second", str(tmp_path / "second"))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.get("/projects")

    assert response.status_code == 200
    assert [project["project_id"] for project in response.json()["projects"]] == [
        first.project_id,
        second.project_id,
    ]


def test_delete_project_endpoint_removes_registered_project(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    delete_response = client.delete(f"/projects/{project.project_id}")
    get_response = client.get(f"/projects/{project.project_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert get_response.status_code == 404
    assert get_response.json() == {"detail": f"project not found: {project.project_id}"}


def test_delete_project_endpoint_returns_404_for_unknown_project():
    runtime = RuntimeService()
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.delete("/projects/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "project not found: missing"}


def test_index_project_endpoint_marks_project_indexed(tmp_path):
    repo_file = tmp_path / "app.py"
    repo_file.write_text("def entrypoint():\n    return 'ok'\n", encoding="utf-8")
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.post(f"/projects/{project.project_id}/index")

    assert response.status_code == 200
    assert response.json()["index_status"] == "indexed"
    assert runtime.get_project_index(project.project_id) is not None


def test_index_project_endpoint_returns_404_for_unknown_project():
    runtime = RuntimeService()
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.post("/projects/missing/index")

    assert response.status_code == 404

