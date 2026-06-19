from __future__ import annotations

import json

from langchain_core.messages import SystemMessage, ToolMessage

from src.graph.prompts import build_answer_prompt, build_step_planning_prompt
from src.graph.state import AgentGraphState
from src.tools.toolkit import ToolResult


def plan_next_step(state: AgentGraphState) -> AgentGraphState:
    chat_model = state.get("chat_model")
    raw_response = ""

    if _has_invoke(chat_model):
        response = chat_model.invoke(build_step_planning_prompt(state))  # type: ignore[union-attr]
        tool_calls = _extract_bound_tool_calls(response)
        if tool_calls:
            return _planned_tool_call_update(state, tool_calls)

        # 如果模型不支持 bind_tools()，不能直接解析出tool_calls字段
        raw_response = _extract_model_content(response)
        tool_calls = _parse_tool_calls(raw_response)
        if tool_calls:
            return _planned_tool_call_update(state, tool_calls)

        next_step = _normalize_next_step(raw_response)
    else:#为 完全没有 LLM 的退化场景 兜底
        next_step = "answer"

    update: dict[str, object] = {"next_step": str(next_step)}
    if next_step == "invalid":
        update["invalid_plan_round"] = int(state.get("invalid_plan_round", 0)) + 1
        update["messages"] = [SystemMessage(content=raw_response, name="invalid_plan")]
    else:
        update["invalid_plan_round"] = 0

    return _append_event(
        update,
        state,
        {"type": "next_step_planned", "next_step": str(next_step)},
    )


def execute_tools(state: AgentGraphState) -> AgentGraphState:
    executor = state.get("tool_executor")
    messages = []
    if callable(executor):
        for index, tool_call in enumerate(state.get("tool_calls", []), start=1):
            try:
                result = executor(tool_call["name"], tool_call.get("arguments", {}))
            except Exception as exc:
                result = ToolResult(
                    ok=False,
                    tool_name=str(tool_call.get("name", "")),
                    error=str(exc),
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
                tool_name=str(tool_call.get("name", "")),
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
    chat_model = state.get("chat_model")
    if _has_invoke(chat_model):
        answer = _extract_model_content(chat_model.invoke(build_answer_prompt(state)))  # type: ignore[union-attr]
    else:
        answer = "Graph execution completed."

    return _append_event(
        {"answer": str(answer)},
        state,
        {"type": "answer_synthesized"},
    )


def validate_answer(state: AgentGraphState) -> AgentGraphState:
    valid = bool(str(state.get("answer", "")).strip())
    reason = "" if valid else "empty answer"

    return _append_event(
        {"status": "completed" if valid else "failed", "reason": reason},
        state,
        {"type": "answer_validated", "valid": valid},
    )


def finish(state: AgentGraphState) -> AgentGraphState:
    update: dict[str, object] = {}
    status = str(state.get("status", "")).strip()
    if status not in {"completed", "failed", "stopped"}:
        update["status"] = "failed"
        update["reason"] = "graph finished without terminal status"
    return _append_event(
        update,
        state,
        {
            "type": "graph_finished",
            "status": str(update.get("status", state.get("status", ""))),
        },
    )


def _planned_tool_call_update(state: AgentGraphState, tool_calls: list[dict[str, object]]) -> AgentGraphState:
    return _append_event(
        {
            "next_step": "execute_tools",
            "tool_calls": tool_calls,
            "invalid_plan_round": 0,
        },
        state,
        {"type": "next_step_planned", "next_step": "execute_tools", "call_count": len(tool_calls)},
    )


def _has_invoke(candidate: object) -> bool:
    return callable(getattr(candidate, "invoke", None))


def _extract_model_content(response: object) -> str:
    return str(getattr(response, "content", response)).strip()


def _extract_bound_tool_calls(response: object) -> list[dict[str, object]]:
    raw_tool_calls = getattr(response, "tool_calls", []) or []
    tool_calls: list[dict[str, object]] = []
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = item.get("name")
            arguments = item.get("args", item.get("arguments", {}))
        else:
            name = getattr(item, "name", "")
            arguments = getattr(item, "args", getattr(item, "arguments", {}))
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(arguments, dict):
            arguments = {}
        tool_calls.append({"name": name, "arguments": arguments})
    return tool_calls


def _normalize_next_step(raw_step: str) -> str:
    normalized = raw_step.strip().lower()
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


def _append_event(
    update: dict[str, object],
    state: AgentGraphState,
    event: dict[str, object],
) -> AgentGraphState:
    return {
        **update,
        "events": [*state.get("events", []), event],
    }
