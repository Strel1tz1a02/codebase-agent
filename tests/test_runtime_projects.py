import pytest

from src.core.errors import ProjectNotFoundError
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


def test_runtime_service_uses_store_instead_of_flat_maps():
    runtime = RuntimeService()

    assert hasattr(runtime, "graph")
    assert hasattr(runtime, "store")
    assert not hasattr(runtime, "_projects")
    assert not hasattr(runtime, "_sessions")
    assert not hasattr(runtime, "_runs")
    assert not hasattr(runtime, "_events_by_run_id")


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
