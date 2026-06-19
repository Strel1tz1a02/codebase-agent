from src.runtime.events import RunEvent
from src.runtime.project import Project
from src.runtime.run import Run
from src.runtime.session import RuntimeSession
from src.runtime.store import RuntimeStore


def test_runtime_store_persists_projects_sessions_runs_and_events(tmp_path):
    """验证 RuntimeStore 可以把平台运行状态写入磁盘并重新加载。"""
    storage_path = tmp_path / "runtime_store.json"
    store = RuntimeStore(storage_path=storage_path)
    project = Project(project_id="project-1", name="demo", repo_path=str(tmp_path))
    session = RuntimeSession(session_id="session-1")
    run = Run(
        run_id="run-1",
        session_id=session.session_id,
        question="Where is main?",
        status="completed",
        answer="main is in src/main.py",
        reason="",
    )
    run.add_event(
        RunEvent(
            event_id="event-1",
            event_type="graph_finish",
            payload={"status": "completed"},
        )
    )
    session.add_run(run)
    project.add_session(session)

    store.add_project(project)

    loaded = RuntimeStore.load(storage_path)
    loaded_project = loaded.get_project(project.project_id)
    loaded_session = loaded_project.get_session(session.session_id)
    loaded_run = loaded_session.get_run(run.run_id)

    assert loaded_project.name == "demo"
    assert loaded_project.repo_path == str(tmp_path)
    assert loaded_run.question == "Where is main?"
    assert loaded_run.status == "completed"
    assert loaded_run.answer == "main is in src/main.py"
    assert loaded_run.events[0].event_type == "graph_finish"
    assert loaded_run.events[0].payload == {"status": "completed"}


def test_runtime_store_does_not_restore_unpersisted_rag_index(tmp_path):
    """验证 RuntimeStore 重启后不会把内存 RAG index 状态伪装成已恢复。"""
    storage_path = tmp_path / "runtime_store.json"
    store = RuntimeStore(storage_path=storage_path)
    project = Project(
        project_id="project-1",
        name="demo",
        repo_path=str(tmp_path),
        index_status="indexed",
    )

    store.add_project(project)

    loaded = RuntimeStore.load(storage_path)
    loaded_project = loaded.get_project(project.project_id)

    assert loaded_project.index_status == "not_indexed"
    assert loaded_project.index is None


def test_runtime_objects_convert_to_and_from_payload(tmp_path):
    project = Project(project_id="project-1", name="demo", repo_path=str(tmp_path))
    session = RuntimeSession(session_id="session-1")
    run = Run(
        run_id="run-1",
        session_id=session.session_id,
        question="Where is main?",
        status="completed",
        answer="main is in src/main.py",
    )
    run.add_event(RunEvent(event_id="event-1", event_type="graph_finish", payload={"ok": True}))
    session.add_run(run)
    project.add_session(session)

    restored = Project.from_payload(project.to_payload())
    restored_session = restored.get_session(session.session_id)
    restored_run = restored_session.get_run(run.run_id)

    assert restored.project_id == project.project_id
    assert restored.repo_path == str(tmp_path)
    assert restored_run.answer == "main is in src/main.py"
    assert restored_run.events[0].payload == {"ok": True}


def test_runtime_store_normalizes_storage_path_to_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    store = RuntimeStore(storage_path="runtime_store.json")
    loaded = RuntimeStore.load("runtime_store.json")

    assert store.storage_path == tmp_path / "runtime_store.json"
    assert loaded.storage_path == tmp_path / "runtime_store.json"
