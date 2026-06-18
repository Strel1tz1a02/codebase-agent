from __future__ import annotations

from src.graph.state import AgentGraphState

_OBSERVATION_TRUNCATE_LIMIT = 2000


def _truncate(text: str, max_chars: int = _OBSERVATION_TRUNCATE_LIMIT) -> str:
    """截断过长文本，附带截断标记，避免单条 observation 撑爆 prompt。"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n...(已截断，原文共 {len(text)} 字符)"


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


def _count_tool_messages(state: AgentGraphState, name: str) -> int:
    """统计指定 name 的 tool message 数量，用于 prompt 中告知 LLM 已有多少轮结果。"""
    return sum(1 for message in _tool_messages(state) if _message_name(message) == name)


def _count_non_retrieval_tool_messages(state: AgentGraphState) -> int:
    """统计非检索类的 tool message 数量（即 read_file/search_code 等工具结果数）。"""
    return sum(
        1
        for message in _tool_messages(state)
        if _message_name(message) != "retrieve_context"
    )


def _calc_remaining_rounds(state: AgentGraphState) -> tuple[int, int]:
    """计算剩余检索次数和剩余工具调用次数。"""
    remaining_retrieval = max(
        0,
        int(state.get("max_retrieval_rounds", 2)) - int(state.get("retrieval_round", 0)),
    )
    remaining_tool = max(
        0,
        int(state.get("max_tool_rounds", 3)) - int(state.get("tool_round", 0)),
    )
    return remaining_retrieval, remaining_tool


def format_tool_results(state: AgentGraphState) -> str:
    """将所有 tool message 格式化为 [工具名]\\n内容 的文本块，供 LLM 消费。"""
    lines = []
    for message in _tool_messages(state):
        name = _message_name(message) or "tool"
        lines.append(f"[{name}]\n{_message_content(message)}")
    return "\n\n".join(lines) if lines else "无"


def format_tool_results_summary(state: AgentGraphState, max_chars_per: int = _OBSERVATION_TRUNCATE_LIMIT) -> str:
    """格式化工具结果摘要，对每条超长内容做截断，供规划节点快速浏览。"""
    lines = []
    for message in _tool_messages(state):
        name = _message_name(message) or "tool"
        content = _message_content(message)
        lines.append(f"[{name}]\n{_truncate(content, max_chars_per)}")
    return "\n\n".join(lines) if lines else "无"


def build_step_planning_prompt(state: AgentGraphState) -> str:
    """构造 plan_next_step 节点的 prompt，让 LLM 根据已有信息一步决定 retrieve / 工具JSON / answer。"""
    remaining_retrieval, remaining_tool = _calc_remaining_rounds(state)
    has_retrieval = _count_tool_messages(state, "retrieve_context") > 0
    tool_results_text = format_tool_results_summary(state)
    repo_path = str(state.get("repo_path", ""))

    lines = [
        "你是 codebase-agent 的流程规划节点。",
        "",
        "只能输出以下三种之一：",
        "1. retrieve                     —— 需要从当前仓库获取代码上下文（RAG检索）",
        "2. [{\"name\":\"...\",\"arguments\":...}] —— JSON数组，指定要调用的工具",
        "3. answer                       —— 已有信息足够，准备生成回答",
        "",
        "决策规则（按优先级）：",
    ]
    if not has_retrieval and remaining_retrieval > 0:
        lines.append("1. 当前无任何检索结果，优先输出 retrieve")
    else:
        lines.append("1. 已有检索结果，检查以下信息是否足以回答")
    lines.append("2. 信息不足且剩余工具次数 > 0 → 输出 JSON 数组")
    lines.append("3. 信息已经足够 → 输出 answer")
    lines.append("")
    lines.append(f"剩余检索次数：{remaining_retrieval}    剩余工具调用次数：{remaining_tool}")
    if remaining_tool == 0:
        lines.append("⚠ 工具次数已用完，只能输出 answer")
    if remaining_retrieval == 0 and not has_retrieval:
        lines.append("⚠ 检索次数已用完，只能基于当前信息回答或调用工具")
    lines.append("")
    lines.append(f"仓库路径：{repo_path}")
    lines.append("")
    lines.append("可用工具：")
    lines.append(f"  repo_summary  : 了解仓库整体结构、文件数量与类型、关键目录、入口文件候选")
    lines.append(f"                 参数：{{\"repo_path\":\"{repo_path}\"}}")
    lines.append(f"  read_file     : 读取指定文件内容，适合在 repo_summary 定位到关键文件后深入查看")
    lines.append(f"                 参数：{{\"repo_path\":\"{repo_path}\",\"path\":\"相对路径\",\"max_chars\":8000}}")
    lines.append(f"  search_code   : 按关键字搜索代码，scope 可选 src/tests/docs/all")
    lines.append(f"                 参数：{{\"repo_path\":\"{repo_path}\",\"keyword\":\"关键字\",\"scope\":\"src\",\"limit\":20}}")
    lines.append(f"  retrieve_code : 语义检索与 query 最相关的代码片段")
    lines.append(f"                 参数：{{\"repo_path\":\"{repo_path}\",\"query\":\"语义检索描述\",\"top_k\":5}}")
    lines.append("")
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
        "- 如果上下文不足以准确回答，明确说明缺少哪些信息\n"
        "- 禁止编造上下文中不存在的内容\n\n"
        f"用户问题：{latest_user_question(state)}\n\n"
        f"已知代码上下文：\n{context}\n"
    )

