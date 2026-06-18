from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.runs import RuntimeService


def test_create_session_returns_404_for_unknown_project():
    """验证创建 session 时未知 project 会走统一 404 JSON 响应。"""
    app = create_app(runtime=RuntimeService())
    client = TestClient(app)

    response = client.post("/projects/missing/sessions")

    assert response.status_code == 404
    assert response.json() == {"detail": "project not found: missing"}


def test_get_session_returns_404_for_unknown_session(tmp_path):
    """验证查询 session 时未知 session 会走统一 404 JSON 响应。"""
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.get(f"/projects/{project.project_id}/sessions/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "session not found: missing"}
