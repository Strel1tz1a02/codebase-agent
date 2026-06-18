from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from src.graph.prompts import (
    build_answer_prompt,
    build_step_planning_prompt,
    latest_user_question,
)
from src.graph.state import AgentGraphState
from src.rag.retrieval import retrieve_from_index
from src.tools.toolkit import ToolResult


def plan_next_step(state: AgentGraphState) -> AgentGraphState:
    """一次 LLM 调用同时产出 next_step 和 tool_calls：先解析 JSON，失败则用关键词匹配。"""
    chat_model = state.get("chat_model")
    if _has_invoke(chat_model):
        raw_response = _extract_model_content(
            chat_model.invoke(build_step_planning_prompt(state))  # type: ignore[union-attr]
        )
        tool_calls = _parse_tool_calls(raw_response)
        if tool_calls:
            return _append_event(
                {"next_step": "execute_tools", "tool_calls": tool_calls},
                state,
                {"type": "next_step_planned", "next_step": "execute_tools", "call_count": len(tool_calls)},
            )
        next_step = _normalize_next_step(raw_response)
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
            hit.to_dict() if hasattr(hit, "to_dict") else hit
            for hit in retrieve_from_index(
                rag_index,
                latest_user_question(state),
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
            chat_model.invoke(build_answer_prompt(state))  # type: ignore[union-attr]
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


def _has_invoke(candidate: object) -> bool:
    return callable(getattr(candidate, "invoke", None))


def _extract_model_content(response: object) -> str:
    return str(getattr(response, "content", response)).strip()


def _normalize_next_step(raw_step: str) -> str:
    """从 LLM 文本输出中提取下一步：retrieve / answer。工具调用由 JSON 解析提前处理。"""
    normalized = raw_step.strip().lower()
    if "retrieve" in normalized or "检索" in normalized:
        return "retrieve"
    if "answer" in normalized or "回答" in normalized:
        return "answer"
    return "invalid"


def _parse_tool_calls(raw_json: str) -> list[dict[str, object]]:
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
    return {
        **update,
        "events": [*state.get("events", []), event],
    }
