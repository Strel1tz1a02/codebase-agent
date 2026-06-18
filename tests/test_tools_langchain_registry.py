from types import SimpleNamespace

import src.tools.toolkit as toolkit
from src.tools.toolkit import build_tools, format_tool_descriptions


def test_build_tools_contains_expected_names():
    tools = build_tools()
    names = {tool.name for tool in tools}

    assert names == {"repo_summary", "read_file", "search_code", "retrieve_code"}


def test_format_tool_descriptions_follows_registered_tools(monkeypatch):
    """验证工具说明从当前工具列表生成，而不是写死固定工具名。"""
    monkeypatch.setattr(
        toolkit,
        "DEFAULT_TOOLS",
        [SimpleNamespace(name="custom_tool", description="Custom fallback description.")],
    )
    monkeypatch.setattr(toolkit, "TOOL_DESCRIPTIONS", {"custom_tool": "custom_tool: dynamic desc"})

    text = format_tool_descriptions()

    assert "custom_tool: dynamic desc" in text
    assert "repo_summary" not in text
