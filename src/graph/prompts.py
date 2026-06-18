from __future__ import annotations

from src.graph.state import AgentGraphState
from src.tools.toolkit import format_tool_descriptions


def _message_role(message: object) -> str:
    """从 dict 或 LangChain message 对象中提取 role 字段，兼容两种格式。"""
    if isinstance(message, dict):
        return str(message.get("role", ""))
    return str(getattr(message, "type", getattr(message, "role", "")))


def _message_name(message: object) -> str:
    """从 dict 或 LangChain message 对象中提取 name 字段（工具名）。"""
    if isinstance(message, dict):
        return str(message.get("name", ""))
    return str(getattr(message, "name", "") or "")


def _message_content(message: object) -> str:
    """从 dict 或 LangChain message 对象中提取 content 字段。"""
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(getattr(message, "content", ""))


def latest_user_question(state: AgentGraphState) -> str:
    """从 messages 中倒序找到最近一条 user/human 消息，返回其内容。"""
    for message in reversed(state.get("messages", [])):
        role = _message_role(message)
        if role in {"user", "human"}:
            return _message_content(message)
    return ""


def _tool_messages(state: AgentGraphState) -> list[object]:
    """筛选出 messages 中所有 role 为 tool 的消息（含检索结果和工具执行结果）。"""
    return [
        message
        for message in state.get("messages", [])
        if _message_role(message) == "tool"
    ]


def latest_invalid_plan_output(state: AgentGraphState) -> str:
    """从 messages 中倒序找到最近一次无效规划输出，用于下一轮规划 prompt 纠偏。"""
    for message in reversed(state.get("messages", [])):
        if _message_name(message) == "invalid_plan":
            return _message_content(message).strip()
    return ""


def _calc_remaining_tool_rounds(state: AgentGraphState) -> int:
    """计算剩余工具调用次数。"""
    return max(
        0,
        int(state.get("max_tool_rounds", 3)) - int(state.get("tool_round", 0)),
    )


def format_tool_results(state: AgentGraphState) -> str:
    """将所有 tool message 格式化为 [工具名]\\n内容 的文本块，供 LLM 消费。"""
    lines = []
    for message in _tool_messages(state):
        name = _message_name(message) or "tool"
        lines.append(f"[{name}]\n{_message_content(message)}")
    return "\n\n".join(lines) if lines else "无"


def build_step_planning_prompt(state: AgentGraphState) -> str:
    """构造 plan_next_step 节点的 prompt，让 LLM 根据已有信息一步决定工具 JSON 或 answer。"""
    remaining_tool = _calc_remaining_tool_rounds(state)
    invalid_plan_round = int(state.get("invalid_plan_round", 0))
    has_tool_results = len(_tool_messages(state)) > 0
    tool_results_text = format_tool_results(state)
    repo_path = str(state.get("repo_path", ""))

    lines = [
        "你是 codebase-agent 的流程规划节点。",
        "",
        "只能输出以下两种之一：",
        "1. [{\"name\":\"...\",\"arguments\":...}] —— JSON数组，指定要调用的工具",
        "2. answer                       —— 信息足够，准备生成回答",
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
        lines.append("1. 尚无任何信息：根据问题性质选择")
        lines.append("   - 纯知识问题、与仓库代码无关 → answer")
        lines.append("   - 需了解仓库整体结构 → JSON，选择可提供仓库总览的工具")
        lines.append("   - 需搜索特定代码 → JSON，优先选择关键词搜索或读取文件工具，需要语义召回时选择检索工具")
    else:
        lines.append("1. 检查已有信息是否足以回答：")
        lines.append("   - 问题与代码实现有关 → 必须有 .py 源码验证，仅有 docs/ 或 .md 文档描述不算足够")
        lines.append("   - 问题仅询问设计思路或文档内容 → 文档描述即可回答")
    lines.append("2. 信息不足以准确回答：")
    lines.append("   - 缺少代码验证（只有 docs 描述没有 .py 源码） → JSON，选择读取文件工具打开对应 .py 文件")
    lines.append("   - 缺少代码内容 → JSON，优先选择读取文件或关键词搜索工具，需要语义召回时选择检索工具")
    if remaining_tool > 0:
        lines.append("   - 已有工具结果被截断(truncated) → JSON 加大 offset 继续读")
    lines.append("3. 剩余次数为 0 时只能输出 answer")
    lines.append("")
    lines.append(f"剩余工具调用次数：{remaining_tool}")
    if remaining_tool == 0:
        lines.append("⚠ 工具次数已用完，只能输出 answer")
    lines.append("")
    lines.append(f"仓库路径：{repo_path}")
    lines.append("")
    lines.append(format_tool_descriptions())
    lines.append("工具调用原则：一次可规划多工具、先总览再深入、信息够时输出 answer")
    lines.append("")
    lines.append(f"用户问题：{latest_user_question(state)}")
    lines.append("")
    lines.append(f"当前已有信息：\n{tool_results_text}")

    return "\n".join(lines)


def build_answer_prompt(state: AgentGraphState) -> str:
    """构造 synthesize_answer 节点的 prompt，把用户问题和所有已有信息组装成回答上下文。"""
    context = format_tool_results(state)
    return (
        "你是一个代码库分析助手。请基于给定代码上下文回答用户问题。\n"
        "回答要求：\n"
        "- 引用时标注文件路径和行号，例如：src/graph/nodes.py:12-34\n"
        "- 分析代码结构时给出层次清晰的分点说明\n"
        "- docs/*.md 是设计文档，可能与实际代码不一致。优先以 .py 源码为准，文档仅作参考\n"
        "- 如果只有文档描述没有源码验证，标注「以下基于文档描述，未经源码验证」\n"
        "- 如果上下文不足以准确回答，明确说明缺少哪些信息\n"
        "- 禁止编造上下文中不存在的内容\n\n"
        f"用户问题：{latest_user_question(state)}\n\n"
        f"已知代码上下文：\n{context}\n"
    )
