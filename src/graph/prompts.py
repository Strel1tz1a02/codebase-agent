from __future__ import annotations

from src.graph.state import AgentGraphState
from src.tools.toolkit import format_tool_descriptions


def _message_role(message: object) -> str:
    if isinstance(message, dict):
        return str(message.get("role", ""))
    return str(getattr(message, "type", getattr(message, "role", "")))


def _message_name(message: object) -> str:
    if isinstance(message, dict):
        return str(message.get("name", ""))
    return str(getattr(message, "name", "") or "")


def _message_content(message: object) -> str:
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(getattr(message, "content", ""))


def latest_user_question(state: AgentGraphState) -> str:
    for message in reversed(state.get("messages", [])):
        role = _message_role(message)
        if role in {"user", "human"}:
            return _message_content(message)
    return ""


def _tool_messages(state: AgentGraphState) -> list[object]:
    return [
        message
        for message in state.get("messages", [])
        if _message_role(message) == "tool"
    ]


def latest_invalid_plan_output(state: AgentGraphState) -> str:
    for message in reversed(state.get("messages", [])):
        if _message_name(message) == "invalid_plan":
            return _message_content(message).strip()
    return ""


def _calc_remaining_tool_rounds(state: AgentGraphState) -> int:
    return max(
        0,
        int(state.get("max_tool_rounds", 3)) - int(state.get("tool_round", 0)),
    )


def format_tool_results(state: AgentGraphState) -> str:
    lines = []
    for message in _tool_messages(state):
        name = _message_name(message) or "tool"
        lines.append(f"[{name}]\n{_message_content(message)}")
    return "\n\n".join(lines) if lines else "无"


def _memory_summary_text(state: AgentGraphState) -> str:
    return str(state.get("memory_summary", "")).strip() or "无"


def _recent_history_text(state: AgentGraphState) -> str:
    return str(state.get("recent_history", "")).strip() or "无"


def build_step_planning_prompt(state: AgentGraphState) -> str:
    remaining_tool = _calc_remaining_tool_rounds(state)
    invalid_plan_round = int(state.get("invalid_plan_round", 0))
    has_tool_results = len(_tool_messages(state)) > 0
    tool_results_text = format_tool_results(state)
    repo_path = str(state.get("repo_path", ""))

    lines = [
        "你是 codebase-agent 的流程规划节点。",
        "",
        "只能输出以下两种之一：",
        "1. JSON 数组，指定要调用的工具。",
        "2. answer，表示信息足够，准备生成回答。",
        "",
        "历史摘要：",
        _memory_summary_text(state),
        "",
        "最近对话：",
        _recent_history_text(state),
        "",
        "决策规则：",
    ]
    if invalid_plan_round > 0:
        last_invalid_plan_output = latest_invalid_plan_output(state)
        lines.append("0. 上一轮规划输出格式无效，本轮必须严格改正。")
        if last_invalid_plan_output:
            lines.append(f"   上一轮无效输出：{last_invalid_plan_output}")
        lines.append("   禁止解释、寒暄、Markdown 代码块或输出其他文本。")
    if not has_tool_results:
        lines.append("1. 如果历史摘要或最近对话已经足够回答，输出 answer。")
        lines.append("2. 如果问题需要代码证据或仓库结构信息，输出 JSON 数组调用合适工具。")
    else:
        lines.append("1. 检查已有工具结果是否足够回答。")
        lines.append("2. 如果仍缺少代码证据，继续输出 JSON 数组调用合适工具。")
    if remaining_tool > 0:
        lines.append("3. 已有工具结果被截断时，可以继续规划读取后续内容。")
    lines.append("4. 剩余次数为 0 时只能输出 answer。")
    lines.append("")
    lines.append(f"剩余工具调用次数：{remaining_tool}")
    if remaining_tool == 0:
        lines.append("工具次数已用完，只能输出 answer。")
    lines.append("")
    lines.append(f"仓库路径：{repo_path}")
    lines.append("")
    lines.append(format_tool_descriptions())
    lines.append("工具调用原则：一次可规划多工具、先总览再深入、信息足够时输出 answer。")
    lines.append("")
    lines.append(f"用户问题：{latest_user_question(state)}")
    lines.append("")
    lines.append(f"当前工具结果：\n{tool_results_text}")

    return "\n".join(lines)


def build_answer_prompt(state: AgentGraphState) -> str:
    context = format_tool_results(state)
    return (
        "你是一个代码库分析助手。请基于给定历史和代码上下文回答用户问题。\n"
        "回答要求：\n"
        "- 如果问题可以由历史摘要或最近对话直接回答，优先使用历史信息。\n"
        "- 引用代码时标注文件路径和行号，例如：src/graph/nodes.py:12-34。\n"
        "- 分析代码结构时给出层次清晰的分点说明。\n"
        "- docs/*.md 是设计文档，可能与实际代码不一致。优先以 .py 源码为准，文档仅作参考。\n"
        "- 如果只有文档描述没有源码验证，标注“以下基于文档描述，未经源码验证”。\n"
        "- 如果上下文不足以准确回答，明确说明缺少哪些信息。\n"
        "- 禁止编造上下文中不存在的内容。\n\n"
        f"历史摘要：\n{_memory_summary_text(state)}\n\n"
        f"最近对话：\n{_recent_history_text(state)}\n\n"
        f"用户问题：{latest_user_question(state)}\n\n"
        f"已知代码上下文：\n{context}\n"
    )
