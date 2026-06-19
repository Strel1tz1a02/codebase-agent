from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.nodes import (
    execute_tools,
    finish,
    plan_next_step,
    synthesize_answer,
    validate_answer,
)
from src.graph.routing import (
    route_after_finish,
    route_after_plan,
    route_after_synthesis,
    route_after_tool_execution,
    route_after_validation,
)
from src.graph.state import AgentGraphState


def build_graph():
    """
    输入:
        无。
    输出:
        编译后的 LangGraph graph 对象，支持 invoke(state)。
    作用:
        把 plan、execute_tools、answer、validate、finish 节点组装成显式 workflow。
        规划节点合并了工具决策和工具规划，一次 LLM 调用产出 next_step + tool_calls。
    """
    graph = StateGraph(AgentGraphState)
    graph.add_node("plan_next_step", plan_next_step)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("synthesize_answer", synthesize_answer)
    graph.add_node("validate_answer", validate_answer)
    graph.add_node("finish", finish)

    graph.set_entry_point("plan_next_step")
    graph.add_conditional_edges(
        "plan_next_step",
        route_after_plan,
        {
            "execute_tools": "execute_tools",
            "synthesize_answer": "synthesize_answer",
            "plan_next_step": "plan_next_step",
            "finish": "finish",
        },
    )
    graph.add_conditional_edges(
        "execute_tools",
        route_after_tool_execution,
        {"plan_next_step": "plan_next_step"},
    )
    graph.add_conditional_edges(
        "synthesize_answer",
        route_after_synthesis,
        {"validate_answer": "validate_answer"},
    )
    graph.add_conditional_edges(
        "validate_answer",
        route_after_validation,
        {"finish": "finish"},
    )
    graph.add_conditional_edges(
        "finish",
        route_after_finish,
        {END: END},
    )
    return graph.compile()
