from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graph.nodes import (
    execute_tools,
    finish,
    plan_next_step,
    plan_tool_use,
    prepare_context,
    retrieve_context,
    synthesize_answer,
    validate_answer,
)
from src.graph.routing import (
    route_after_finish,
    route_after_plan,
    route_after_prepare,
    route_after_retrieval,
    route_after_synthesis,
    route_after_tool_execution,
    route_after_tool_plan,
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
        把阶段 4 的 prepare、classify、retrieve、tool、answer、validate、finish 节点组装成显式 workflow。
    为什么需要这个函数?
        旧版 agent graph 依赖 decision JSON 协议串联流程；新 graph 需要把状态、节点和路由拆开，
        让后续 runtime、checkpoint 和事件追踪都能围绕标准 state 扩展。
    """
    graph = StateGraph(AgentGraphState)
    graph.add_node("prepare_context", prepare_context)
    graph.add_node("plan_next_step", plan_next_step)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("plan_tool_use", plan_tool_use)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("synthesize_answer", synthesize_answer)
    graph.add_node("validate_answer", validate_answer)
    graph.add_node("finish", finish)

    graph.set_entry_point("prepare_context")
    graph.add_conditional_edges(
        "prepare_context",
        route_after_prepare,
        {"plan_next_step": "plan_next_step"},# {路由结果: 下一节点}
    )
    graph.add_conditional_edges(
        "plan_next_step",
        route_after_plan,
        {
            "retrieve_context": "retrieve_context",
            "plan_tool_use": "plan_tool_use",
            "synthesize_answer": "synthesize_answer",
        },
    )
    graph.add_conditional_edges(
        "retrieve_context",
        route_after_retrieval,
        {"plan_next_step": "plan_next_step"},
    )
    graph.add_conditional_edges(
        "plan_tool_use",
        route_after_tool_plan,
        {"execute_tools": "execute_tools"},
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
