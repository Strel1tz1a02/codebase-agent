from src.cli.main import main


def test_cli_serve_starts_uvicorn(monkeypatch):
    calls = []

    def fake_run(app_path, host, port):
        calls.append({"app_path": app_path, "host": host, "port": port})

    monkeypatch.setattr("src.cli.main.uvicorn.run", fake_run)

    exit_code = main(["--host", "127.0.0.1", "--port", "8001"])

    assert exit_code == 0
    assert calls == [
        {
            "app_path": "src.api.app:app",
            "host": "127.0.0.1",
            "port": 8001,
        }
    ]


def test_cli_serve_defaults(monkeypatch):
    defaults = {}

    def fake_run(app_path, host, port):
        defaults.update({"app_path": app_path, "host": host, "port": port})

    monkeypatch.setattr("src.cli.main.uvicorn.run", fake_run)

    exit_code = main([])

    assert exit_code == 0
    assert defaults == {"app_path": "src.api.app:app", "host": "127.0.0.1", "port": 8000}
