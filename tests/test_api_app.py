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
