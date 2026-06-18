from src.server.main import main


def test_server_launcher_starts_uvicorn(monkeypatch):
    """验证 server launcher 会按传入 host/port 启动 Uvicorn。"""
    calls = []

    def fake_run(app_path, host, port):
        """记录 uvicorn.run 入参，避免测试真正启动服务。"""
        calls.append({"app_path": app_path, "host": host, "port": port})

    monkeypatch.setattr("src.server.main.uvicorn.run", fake_run)

    exit_code = main(["--host", "127.0.0.1", "--port", "8001"])

    assert exit_code == 0
    assert calls == [
        {
            "app_path": "src.api.app:app",
            "host": "127.0.0.1",
            "port": 8001,
        }
    ]


def test_server_launcher_uses_defaults(monkeypatch):
    """验证 server launcher 未传参数时使用默认监听地址。"""
    defaults = {}

    def fake_run(app_path, host, port):
        """记录默认启动参数，避免测试真正启动服务。"""
        defaults.update({"app_path": app_path, "host": host, "port": port})

    monkeypatch.setattr("src.server.main.uvicorn.run", fake_run)

    exit_code = main([])

    assert exit_code == 0
    assert defaults == {"app_path": "src.api.app:app", "host": "127.0.0.1", "port": 8000}
