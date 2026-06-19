from types import SimpleNamespace

import src.tools.toolkit as toolkit
from src.tools.toolkit import DEFAULT_TOOLS, format_tool_descriptions


def test_default_tools_contains_expected_names():
    names = {tool.name for tool in DEFAULT_TOOLS}

    assert names == {
        "repo_summary",
        "read_file",
        "search_code",
        "retrieve_code",
        "read_history_run",
    }


def test_format_tool_descriptions_follows_registered_tools(monkeypatch):
    """验证工具说明从当前工具列表生成，而不是写死固定工具名。"""
    monkeypatch.setattr(
        toolkit,
        "DEFAULT_TOOLS",
        [SimpleNamespace(name="custom_tool", description="Custom fallback description.")],
    )
    text = format_tool_descriptions()

    assert "custom_tool: Custom fallback description." in text
    assert "repo_summary" not in text
