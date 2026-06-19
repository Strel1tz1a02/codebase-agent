from pathlib import Path


def test_ui_loads_and_deletes_projects_from_api():
    """验证前端脚本会从 API 加载项目列表，并调用删除项目接口。"""
    script = Path("src/ui/static/app.js").read_text(encoding="utf-8")

    assert 'await request("/projects")' in script
    assert 'method: "DELETE"' in script
    assert "loadProjects();" in script


def test_ui_sidebar_loads_sessions_and_existing_runs():
    """验证前端侧栏会列出项目会话，并能恢复已有会话的 run 历史。"""
    script = Path("src/ui/static/app.js").read_text(encoding="utf-8")
    markup = Path("src/ui/static/index.html").read_text(encoding="utf-8")

    assert "loadSessions(project.project_id)" in script
    assert "selectSession(projectId, sessionId)" in script
    assert "`/projects/${projectId}/sessions`" in script
    assert "`/projects/${projectId}/sessions/${sessionId}/runs`" in script
    assert 'id="sessionList"' in markup
    assert 'id="newSessionButton"' in markup


def test_ui_sidebar_width_is_user_resizable():
    """验证前端提供可拖拽边栏宽度，并会保存用户调整。"""
    script = Path("src/ui/static/app.js").read_text(encoding="utf-8")
    markup = Path("src/ui/static/index.html").read_text(encoding="utf-8")
    styles = Path("src/ui/static/styles.css").read_text(encoding="utf-8")

    assert 'id="sidebarResizer"' in markup
    assert "initSidebarResize()" in script
    assert "codebase-agent.sidebarWidth" in script
    assert "--sidebar-width" in styles


def test_ui_can_delete_individual_sessions():
    """验证前端会调用删除单个会话的 API，而不是只能删除整个项目。"""
    script = Path("src/ui/static/app.js").read_text(encoding="utf-8")

    assert "deleteSession(projectId, session)" in script
    assert "`/projects/${projectId}/sessions/${session.session_id}`" in script
    assert 'method: "DELETE"' in script
