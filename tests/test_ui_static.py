from pathlib import Path


def test_ui_loads_and_deletes_projects_from_api():
    """验证前端脚本会从 API 加载项目列表，并调用删除项目接口。"""
    script = Path("src/ui/static/app.js").read_text(encoding="utf-8")

    assert 'await request("/projects")' in script
    assert 'method: "DELETE"' in script
    assert "loadProjects();" in script
