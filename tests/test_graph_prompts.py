from src.graph.prompts import build_answer_prompt, build_step_planning_prompt
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


def test_prompts_include_memory_summary_and_recent_history():
    state = create_initial_state(
        "demo",
        "E:/repo",
        "我叫什么",
        rag_index=None,
        chat_model=None,
        tool_executor=None,
    )
    state["memory_summary"] = "用户信息：\n- 用户自称 L。"
    state["recent_history"] = "用户：我叫L\n助手：你好，L！"

    planning_prompt = build_step_planning_prompt(state)
    answer_prompt = build_answer_prompt(state)

    assert "用户自称 L" in planning_prompt
    assert "用户：我叫L" in planning_prompt
    assert "用户自称 L" in answer_prompt
    assert "用户：我叫L" in answer_prompt
