from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from src.graph.state import AgentGraphState
from src.rag.retrieval import retrieve_from_index
from src.tools.registry import ToolResult


def plan_next_step(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 chat_model。
    输出:
        写入 next_step 并追加 next_step_planned 事件后的 AgentGraphState。
    作用:
        根据当前问题、检索结果和工具结果规划下一步是检索、工具调用，还是生成回答。
    为什么需要这个函数?
        ReAct 风格流程需要在每次 observation 后重新思考下一步；统一规划节点可以让 RAG 和工具结果都回到同一个决策点。
    """
    chat_model = state.get("chat_model")
    if _has_invoke(chat_model):
        next_step = _normalize_next_step(
            _extract_model_content(chat_model.invoke(_build_step_planning_prompt(state)))  # type: ignore[union-attr]
        )
    else:
        next_step = "answer"
    return _append_event(
        {"next_step": str(next_step)},
        state,
        {"type": "next_step_planned", "next_step": str(next_step)},
    )


def retrieve_context(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 retriever。
    输出:
        追加检索 observation message 并记录 retrieval_round 后的 AgentGraphState update。
    作用:
        根据用户问题和仓库路径获取相关代码片段，供回答生成或工具规划使用。
    为什么需要这个函数?
        RAG 检索应作为独立节点存在，召回数量等检索策略应由 retriever 自己决定，graph 只负责编排。
    """
    retrieval_round = int(state.get("retrieval_round", 0)) + 1
    rag_index = state.get("rag_index")
    if rag_index is not None:
        hits = [
            hit.to_dict() if hasattr(hit, "to_dict") else hit# hasattr:是否有这个属性或方法
            for hit in retrieve_from_index(
                rag_index,
                _latest_user_question(state),
                int(state.get("retrieval_top_k", 5)),
            )
        ]
    else:
        hits = []

    retrieval_message = ToolMessage(
        content=_format_retrieval_hits(list(hits)),
        name="retrieve_context",
        tool_call_id=f"retrieve_context:{retrieval_round}",
    )
    return _append_event(
        {"retrieval_round": retrieval_round, "messages": [retrieval_message]},
        state,
        {"type": "context_retrieved", "hit_count": len(hits)},
    )


def plan_tool_use(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 chat_model。
    输出:
        写入 tool_calls 并追加 tool_use_planned 事件后的 AgentGraphState。
    作用:
        基于当前上下文、检索结果和问题规划需要执行的工具调用。
    为什么需要这个函数?
        工具规划和工具执行需要分开；这样 graph 可以在执行前检查、记录或跳过空 tool_calls。
    """
    chat_model = state.get("chat_model")
    if _has_invoke(chat_model):
        tool_calls = _parse_tool_calls(
            _extract_model_content(chat_model.invoke(_build_tool_planning_prompt(state)))  # type: ignore[union-attr]
        )
    else:
        tool_calls = []
    return _append_event(
        {"tool_calls": list(tool_calls)},
        state,
        {"type": "tool_use_planned", "call_count": len(tool_calls)},
    )


def execute_tools(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，包含 tool_calls，可选包含 tool_executor。
    输出:
        追加工具 observation message 并记录 tool_round 后的 AgentGraphState update。
    作用:
        顺序执行已经规划好的工具调用，并把结果保存回 state。
    为什么需要这个函数?
        本地工具执行是可观察的副作用步骤，单独成节点后可以独立测试 fake executor，
        也方便后续做权限、错误处理和事件追踪。
    """
    executor = state.get("tool_executor")
    messages = []
    if callable(executor):
        for index, tool_call in enumerate(state.get("tool_calls", []), start=1):
            try:
                result = executor(
                    tool_call["name"], tool_call.get("arguments", {})
                )
            except Exception as e:
                result = ToolResult(
                    ok=False,
                    tool_name=tool_call.get("name", ""),
                    error=str(e),
                )
            messages.append(
                ToolMessage(
                    content=str(result),
                    name=str(tool_call.get("name", "")),
                    tool_call_id=f"{tool_call.get('name', 'tool')}:{index}",
                )
            )
    else:
        for index, tool_call in enumerate(state.get("tool_calls", []), start=1):
            result = ToolResult(
                ok=False,
                tool_name=tool_call.get("name", ""),
                error="No tool executor configured.",
            )
            messages.append(
                ToolMessage(
                    content=str(result),
                    name=str(tool_call.get("name", "")),
                    tool_call_id=f"{tool_call.get('name', 'tool')}:{index}",
                )
            )
    return _append_event(
        {
            "tool_round": int(state.get("tool_round", 0)) + 1,
            "messages": messages,
        },
        state,
        {"type": "tools_executed", "result_count": len(messages)},
    )


def synthesize_answer(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 chat_model。
    输出:
        写入 answer 并追加 answer_synthesized 事件后的 AgentGraphState。
    作用:
        根据当前 state 生成最终回答；未配置模型时返回阶段 4 的默认占位回答。
    为什么需要这个函数?
        回答生成是 graph 的核心收束节点，通过 chat_model.invoke() 接入真实模型或测试模型。
    """
    chat_model = state.get("chat_model")
    if _has_invoke(chat_model):
        answer = _extract_model_content(
            chat_model.invoke(_build_answer_prompt(state))  # type: ignore[union-attr]
        )
    else:
        answer = "Graph execution completed."

    return _append_event(
        {"answer": str(answer)},
        state,
        {"type": "answer_synthesized"},
    )


def validate_answer(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，至少包含 answer。
    输出:
        写入 status、reason 并追加 answer_validated 事件后的 AgentGraphState。
    作用:
        校验回答是否可接受，成功时标记 completed，失败时标记 failed。
    为什么需要这个函数?
        校验独立成节点后，后续可以加入引用检查、空回答检查或安全规则，而不污染回答生成逻辑。
    """
    valid = bool(str(state.get("answer", "")).strip())
    reason = "" if valid else "empty answer"

    return _append_event(
        {"status": "completed" if valid else "failed", "reason": reason},
        state,
        {"type": "answer_validated", "valid": valid},
    )


def finish(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: validate_answer 后的 AgentGraphState。
    输出:
        追加 graph_finished 事件后的 AgentGraphState。
    作用:
        统一记录 graph 结束事件，并在缺少 status 时补成 completed。
    为什么需要这个函数?
        结束节点让 runtime 后续可以稳定消费 graph 完成事件，而不是从多个业务节点里推断结束状态。
    """
    update: dict[str, object] = {}
    if not str(state.get("status", "")):
        update["status"] = "completed"
    return _append_event(
        update,
        state,
        {
            "type": "graph_finished",
            "status": str(update.get("status", state.get("status", ""))),
        },
    )


def _latest_user_question(state: AgentGraphState) -> str:
    """
    输入:
        state: 当前 AgentGraphState，包含 messages。
    输出:
        str: 最近一条 user 消息内容；不存在时返回空字符串。
    作用:
        为上下文准备和检索节点提供统一的问题提取逻辑。
    为什么需要这个函数?
        messages 是标准对话结构，集中读取可以避免每个节点重复写倒序查找逻辑。
    """
    for message in reversed(state.get("messages", [])):
        role = _message_role(message)
        if role in {"user", "human"}:
            return _message_content(message)
    return ""


def _has_invoke(candidate: object) -> bool:
    """
    输入:
        candidate: 可能的 LangChain chat model。
    输出:
        bool: 是否提供 invoke 方法。
    作用:
        让 graph 节点通过统一的 LangChain invoke 接口调用真实模型或测试模型。
    为什么需要这个函数?
        LangChain chat model 通常不是普通 callable，而是通过 invoke(prompt/messages) 调用。
    """
    return callable(getattr(candidate, "invoke", None))


def _extract_model_content(response: object) -> str:
    """
    输入:
        response: LangChain 模型返回值或测试 fake 返回值。
    输出:
        str: 可写入 graph state 的文本。
    作用:
        统一提取 AIMessage.content，并兼容普通字符串。
    为什么需要这个函数?
        不同模型返回对象略有差异，节点只需要稳定的文本答案。
    """
    return str(getattr(response, "content", response)).strip()# getattr:获取对象属性，提供默认值,默认值是 response 本身，适用于 response 是字符串的情况。


def _normalize_next_step(raw_step: str) -> str:
    """
    输入:
        raw_step: LLM 返回的下一步文本。
    输出:
        str: retrieve、tool 或 answer。
    作用:
        把模型输出约束到 routing 支持的三个分支。
    为什么需要这个函数?
        模型可能返回解释性文本，路由层只接受稳定枚举。
    """
    normalized = raw_step.strip().lower()
    if "retrieve" in normalized or "检索" in normalized:
        return "retrieve"
    if "tool" in normalized or "工具" in normalized:
        return "tool"
    if "answer" in normalized or "回答" in normalized:
        return "answer"
    return "invalid"


def _build_step_planning_prompt(state: AgentGraphState) -> str:
    """
    输入:
        state: 当前 graph state。
    输出:
        str: 规划节点使用的 LLM prompt。
    作用:
        让模型根据问题和当前 observation 决定下一步。
    为什么需要这个函数?
        planning prompt 独立后，后续可以单独测试和演进提示词，而不污染节点主流程。
    """
    return (
        "你是 codebase-agent 的流程规划节点。\n"
        "只能回答一个词：retrieve、tool 或 answer。\n"
        "规则：如果还没有检索上下文，优先回答 retrieve；如果需要读取具体文件或搜索代码，回答 tool；"
        "如果已有足够上下文可以总结，回答 answer。\n\n"
        f"用户问题：{_latest_user_question(state)}\n"
        f"检索结果数量：{_count_tool_messages(state, 'retrieve_context')}\n"
        f"工具结果数量：{_count_non_retrieval_tool_messages(state)}\n"
    )


def _build_answer_prompt(state: AgentGraphState) -> str:
    """
    输入:
        state: 当前 graph state。
    输出:
        str: 回答生成节点使用的 LLM prompt。
    作用:
        把用户问题、RAG 命中和工具结果整理成模型可消费的上下文。
    为什么需要这个函数?
        回答生成不应直接把整个 state 交给模型；显式 prompt 可以控制上下文和引用格式。
    """
    observation_context = _format_observation_messages(state)
    return (
        "你是一个代码库分析助手。请基于给定代码上下文回答用户问题。\n"
        "要求：优先引用文件路径和行号；如果上下文不足，明确说明缺少什么。\n\n"
        f"用户问题：{_latest_user_question(state)}\n\n"
        f"已知 observation：\n{observation_context}\n"
    )


def _build_tool_planning_prompt(state: AgentGraphState) -> str:
    """
    输入:
        state: 当前 graph state。
    输出:
        str: 工具规划节点使用的 LLM prompt。
    作用:
        让模型在需要时输出结构化工具调用。
    为什么需要这个函数?
        工具规划需要严格 JSON 输出，独立 prompt 便于约束格式和测试。
    """
    return (
        "你是 codebase-agent 的工具规划节点。\n"
        "可用工具：repo_summary、read_file、search_code、retrieve_code。\n"
        "所有工具都需要 repo_path 参数（值为当前仓库路径）。\n"
        "参数说明：\n"
        "- repo_summary: repo_path\n"
        '- read_file: repo_path, path（必填，相对路径）, max_chars（可选）\n'
        '- search_code: repo_path, keyword（必填）, scope（可选）, limit（可选）\n'
        '- retrieve_code: repo_path, query（必填）, top_k（可选）\n'
        "只返回 JSON 数组，不要返回解释。数组元素格式："
        '{"name":"工具名","arguments":{...}}。如果不需要工具，返回 []。\n\n'
        f"当前仓库路径：{state.get('repo_path', '')}\n\n"
        f"用户问题：{_latest_user_question(state)}\n\n"
        f"已有 observation：\n{_format_observation_messages(state)}\n"
    )


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


def _tool_messages(state: AgentGraphState) -> list[object]:
    return [
        message
        for message in state.get("messages", [])
        if _message_role(message) == "tool"
    ]


def _count_tool_messages(state: AgentGraphState, name: str) -> int:
    return sum(1 for message in _tool_messages(state) if _message_name(message) == name)


def _count_non_retrieval_tool_messages(state: AgentGraphState) -> int:
    return sum(
        1
        for message in _tool_messages(state)
        if _message_name(message) != "retrieve_context"
    )


def _format_observation_messages(state: AgentGraphState) -> str:
    lines = []
    for message in _tool_messages(state):
        name = _message_name(message) or "tool"
        lines.append(f"[{name}]\n{_message_content(message)}")
    return "\n\n".join(lines) if lines else "无"


def _parse_tool_calls(raw_json: str) -> list[dict[str, object]]:
    """
    输入:
        raw_json: LLM 返回的 JSON 数组文本。
    输出:
        list[dict[str, object]]: 标准 tool_calls。
    作用:
        把模型输出约束为 execute_tools 可消费的结构。
    为什么需要这个函数?
        工具执行层不能直接信任模型输出，进入执行前需要做最小结构校验。
    """
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []

    tool_calls: list[dict[str, object]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        arguments = item.get("arguments", {})
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(arguments, dict):
            arguments = {}
        tool_calls.append({"name": name, "arguments": arguments})
    return tool_calls


def _format_retrieval_hits(hits: object) -> str:
    if not isinstance(hits, list) or not hits:
        return "无"
    lines = []
    for index, hit in enumerate(hits, start=1):
        if not isinstance(hit, dict):
            continue
        relative_path = str(hit.get("relative_path", ""))
        start_line = int(hit.get("start_line", 0) or 0)
        end_line = int(hit.get("end_line", 0) or 0)
        content = str(hit.get("content", ""))
        lines.append(f"{index}. {relative_path}:{start_line}-{end_line}\n{content}")
    return "\n\n".join(lines) if lines else "无"


def _append_event(
    update: dict[str, object],
    state: AgentGraphState,
    event: dict[str, object],
) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState。
        event: 要追加的事件字典。
    输出:
        追加事件后的 AgentGraphState。
    作用:
        以不可变风格复制 state，并把新事件追加到 events 列表末尾。
    为什么需要这个函数?
        graph 节点都需要写事件；集中处理可以保证事件追加方式一致，避免误改原始 state。
    """
    return {
        **update,
        "events": [*state.get("events", []), event],
    }
