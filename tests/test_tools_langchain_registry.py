from src.tools.registry import build_tools


def test_build_tools_contains_expected_names():
    tools = build_tools()
    names = {tool.name for tool in tools}

    assert names == {"repo_summary", "read_file", "search_code", "retrieve_code"}

