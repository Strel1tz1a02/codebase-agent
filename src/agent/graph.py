from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, StateGraph

from src.agent.nodes import (
    decide_next_action,
    execute_selected_tool,
    route_after_decision,
    route_after_tool,
)
from src.agent.state import AgentGraphState
from src.tools.registry import TOOL_REGISTRY


def build_agent_graph():
    """
    输入:
        无。
    输出:
        编译后的 LangGraph graph 对象，支持 invoke(state)。
    作用:
        用 StateGraph 把 decide_next_action、execute_selected_tool 和两个路由函数
        组装成真正的 LangGraph workflow。
    为什么需要这个函数:
        本地 while runner 已经验证了流程；现在把同样的节点和路由交给 LangGraph
        编排，后续才能继续学习 checkpoint、可视化和更复杂的条件边。
    """
    workflow = StateGraph(AgentGraphState)
    workflow.add_node("decide_next_action", decide_next_action)
    workflow.add_node("execute_selected_tool", execute_selected_tool)

    workflow.set_entry_point("decide_next_action")
    workflow.add_conditional_edges(
        "decide_next_action",  # 从 decide_next_action 节点出发。
        route_after_decision,  # 节点执行完后，用这个函数根据 state 判断下一步去哪。
        {
            "tool": "execute_selected_tool",
            "end": END,
        },
    )
    workflow.add_conditional_edges(
        "execute_selected_tool",
        route_after_tool,
        {
            "decision": "decide_next_action",
            "end": END,
        },
    )
    return workflow.compile()


def _build_initial_state(
    question: str,
    repo_path: str,
    llm_decision_func: Callable[[dict[str, object]], dict[str, object]],
    max_steps: int,
    messages: list[dict[str, str]] | None = None,
) -> AgentGraphState:
    """
    输入:
        question: 用户问题。
        repo_path: 要分析的仓库路径。
        llm_decision_func: LLM 决策函数。
        max_steps: 最大工具调用步数。
        messages: Runtime 传入的多轮对话消息。
    输出:
        AgentGraphState 初始状态字典。
    作用:
        准备本地 graph runner 第一次进入 decide_next_action 前需要的 state。
    为什么需要这个函数:
        graph 的入口需要一个完整初始 state。把初始化单独放在函数里，可以避免
        run_agent_graph 里混杂太多字段细节。
    """
    return {
        "question": question,
        "repo_path": repo_path,
        "messages": list(messages or []),
        "allowed_tools": list(TOOL_REGISTRY.keys()),
        "history": [],
        "decision": {},
        "tool_result": {},
        "answer": "",
        "status": "",
        "reason": "",
        "step_count": 0,
        "max_steps": max_steps,
        "llm_decision_func": llm_decision_func,
    }


def _to_result(state: AgentGraphState) -> dict[str, object]:
    """
    输入:
        state: graph runner 停止时的最终状态。
    输出:
        dict[str, object]，与 V3 run_agent_loop 的返回结构对齐。
    作用:
        把内部 state 转成外部调用方更容易消费的结果。
    为什么需要这个函数:
        graph 内部 state 字段比最终返回值更多。对外保持 V3 风格，可以降低
        后续 CLI 接入成本。
    """
    result: dict[str, object] = {
        "status": state.get("status", "stopped"),
        "answer": state.get("answer", ""),
        "history": state.get("history", []),
    }
    reason = str(state.get("reason", ""))
    if reason:
        result["reason"] = reason
    return result


def _is_max_steps_reached(state: AgentGraphState) -> bool:
    """
    输入:
        state: LangGraph invoke 后的最终状态。
    输出:
        bool: 是否因为工具调用步数达到 max_steps 而停止。
    作用:
        显式判断 max_steps 停止原因。
    为什么需要这个函数:
        LangGraph 走到 END 时不一定代表完成回答；如果 status 仍为空，并且
        step_count >= max_steps，说明这次结束来自步数上限。
    """
    if str(state.get("status", "")):
        return False

    step_count = int(state.get("step_count", 0))
    max_steps = int(state.get("max_steps", 3))
    return step_count >= max_steps


def run_agent_graph(
    question: str,
    repo_path: str,
    llm_decision_func: Callable[[dict[str, object]], dict[str, object]],
    max_steps: int = 3,
    messages: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """
    输入:
        question: 用户问题。
        repo_path: 要分析的仓库路径。
        llm_decision_func: 可注入的 LLM 决策函数，输入 context 字典，输出 decision 字典。
        max_steps: 最大工具调用步数。
        messages: Runtime 传入的多轮对话消息。
    输出:
        dict[str, object]，包含 status、answer、history，停止时还包含 reason。
    作用:
        用普通 while 循环模拟 LangGraph 的节点流转。
    为什么需要这个函数:
        在正式引入 LangGraph 之前，先用本地 runner 验证 state、node 和 route 的
        设计是否正确。理解清楚后，再替换成 StateGraph 会更容易。
    """
    state = _build_initial_state(
        question=question,
        repo_path=repo_path,
        llm_decision_func=llm_decision_func,
        max_steps=max_steps,
        messages=messages,
    )

    graph = build_agent_graph()
    final_state = graph.invoke(state)
    if _is_max_steps_reached(final_state):
        final_state["status"] = "stopped"
        final_state["answer"] = ""
        final_state["reason"] = "max_steps reached"
    return _to_result(final_state)
