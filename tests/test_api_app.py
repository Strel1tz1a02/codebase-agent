from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.runs import RuntimeService


def test_health_returns_ok():
    app = create_app(runtime=RuntimeService())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_app_uses_runtime_service_only():
    runtime = RuntimeService()

    app = create_app(runtime=runtime)

    assert app.state.runtime is runtime
    assert not hasattr(app.state, "project_runtime")


def test_ui_page_serves_static_app():
    app = create_app(runtime=RuntimeService())
    client = TestClient(app)

    response = client.get("/ui")

    assert response.status_code == 200
    assert "codebase-agent" in response.text
    assert 'lang="zh-CN"' in response.text
    assert "项目" in response.text
    assert "/ui/static/app.js" in response.text
    assert "/ui/static/styles.css" in response.text
