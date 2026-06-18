from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.service import RuntimeService


def test_create_session_returns_404_for_unknown_project():
    """楠岃瘉鍒涘缓 session 鏃舵湭鐭?project 浼氳蛋缁熶竴 404 JSON 鍝嶅簲銆?""
    app = create_app(runtime=RuntimeService())
    client = TestClient(app)

    response = client.post("/projects/missing/sessions")

    assert response.status_code == 404
    assert response.json() == {"detail": "project not found: missing"}


def test_get_session_returns_404_for_unknown_session(tmp_path):
    """楠岃瘉鏌ヨ session 鏃舵湭鐭?session 浼氳蛋缁熶竴 404 JSON 鍝嶅簲銆?""
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))
    app = create_app(runtime=runtime)
    client = TestClient(app)

    response = client.get(f"/projects/{project.project_id}/sessions/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "session not found: missing"}

