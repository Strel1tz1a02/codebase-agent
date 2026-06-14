from __future__ import annotations

from typing import TypedDict


class AgentGraphState(TypedDict, total=False):
    """
    输入:
        LangGraph 在每个节点之间传递的共享 state 字典。
    输出:
        TypedDict 类型定义，不在运行时直接产出数据。
    作用:
        约束阶段 4 新 graph 使用的标准字段，包括 messages、retrieval_hits、tool_calls 和 events。
    为什么需要这个类型?
        旧链路字段分散在 agent/runtime 中；新 graph 需要一个清晰的 state 契约，方便节点、路由和测试共享。
    """

    project_id: str
    repo_path: str
    messages: list[dict[str, str]]
    context: dict[str, object]
    next_step: str #用于规划节点的输出，指导后续检索、工具调用或回答
    retrieval_round: int
    retrieval_hits: list[dict[str, object]]
    tool_calls: list[dict[str, object]]
    tool_results: list[dict[str, object]]
    answer: str
    status: str
    reason: str
    events: list[dict[str, object]]
    retrieval_top_k: int
    step_planner: object
    rag_index: object
    tool_planner: object
    tool_executor: object
    chat_model: object
    answer_validator: object


def create_initial_state(
    project_id: str,
    repo_path: str,
    question: str,
) -> AgentGraphState:
    """
    输入:
        project_id: 项目标识。
        repo_path: 仓库根目录路径。
        question: 用户本轮问题。
    输出:
        AgentGraphState: graph 首次 invoke 时使用的初始状态。
    作用:
        初始化标准 messages、检索结果、工具调用、回答、状态和事件字段。
    为什么需要这个函数?
        graph 入口需要稳定完整的 state；集中初始化可以避免 runtime 或测试手写字段时遗漏默认值。
    """
    return {
        "project_id": project_id,
        "repo_path": repo_path,
        "messages": [{"role": "user", "content": question}],
        "retrieval_hits": [],
        "tool_calls": [],
        "tool_results": [],
        "answer": "",
        "status": "running",
        "reason": "",
        "events": [],
    }
