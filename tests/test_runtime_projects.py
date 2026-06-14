import pytest

from src.core.errors import ProjectNotFoundError
from src.rag.schemas import RagIndex
from src.runtime.runs import RuntimeService


def test_runtime_creates_and_loads_project(tmp_path):
    runtime = RuntimeService()

    project = runtime.create_project("demo", str(tmp_path))
    loaded = runtime.get_project(project.project_id)

    assert loaded is project
    assert project.name == "demo"
    assert project.repo_path == str(tmp_path)
    assert project.index_status == "not_indexed"
    assert runtime.store.projects[project.project_id] is project
    assert project.sessions == {}
    assert runtime.get_project_index(project.project_id) is None


def test_runtime_service_uses_store_instead_of_flat_maps():
    runtime = RuntimeService()

    assert hasattr(runtime, "graph")
    assert hasattr(runtime, "store")
    assert not hasattr(runtime, "_projects")
    assert not hasattr(runtime, "_sessions")
    assert not hasattr(runtime, "_runs")
    assert not hasattr(runtime, "_events_by_run_id")
    assert hasattr(runtime.store, "project_indexes")


def test_runtime_rejects_unknown_project():
    runtime = RuntimeService()

    with pytest.raises(ProjectNotFoundError):
        runtime.get_project("missing")


def test_runtime_validates_project_exists(tmp_path):
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))

    runtime.validate_project_exists(project.project_id)

    with pytest.raises(ProjectNotFoundError):
        runtime.validate_project_exists("missing")


def test_runtime_index_project_builds_rag_index(tmp_path):
    repo_file = tmp_path / "app.py"
    repo_file.write_text("def entrypoint():\n    return 'ok'\n", encoding="utf-8")
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))

    indexed = runtime.index_project(project.project_id)

    assert indexed.index_status == "indexed"
    assert runtime.get_project_index(project.project_id) is not None


def test_runtime_index_project_delegates_to_rag_layer(tmp_path, monkeypatch):
    calls: list[dict[str, str]] = []
    fake_index = RagIndex(
        project_id="demo",
        repo_path=str(tmp_path),
        vector_store=object(),
        document_count=0,
    )

    def fake_build_project_index(project_id: str, repo_path: str):
        calls.append({"project_id": project_id, "repo_path": repo_path})
        return fake_index

    monkeypatch.setattr("src.runtime.runs.build_project_index", fake_build_project_index)
    runtime = RuntimeService()
    project = runtime.create_project("demo", str(tmp_path))

    indexed = runtime.index_project(project.project_id)

    assert indexed.index_status == "indexed"
    assert calls == [{"project_id": project.project_id, "repo_path": str(tmp_path)}]
    assert runtime.get_project_index(project.project_id) is fake_index
