from src.graph.prompts import build_step_planning_prompt
from src.graph.state import create_initial_state


def test_step_planning_prompt_gets_tool_names_only_from_tool_description_block():
    """验证规划规则不硬编码工具名，工具名只来自动态工具说明块。"""
    state = create_initial_state(
        "demo",
        "E:/repo",
        "Where is main?",
        rag_index=None,
        chat_model=None,
        tool_executor=None,
    )

    prompt = build_step_planning_prompt(state)
    rules_text, tool_text = prompt.split("可用工具：", 1)

    for tool_name in ["repo_summary", "read_file", "search_code", "retrieve_code"]:
        assert tool_name not in rules_text
        assert tool_name in tool_text
