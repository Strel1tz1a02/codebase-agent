from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentGraphState(TypedDict, total=False):
    """
    输入:
        LangGraph 在每个节点之间传递的共享 state 字典。
    输出:
        TypedDict 类型定义，不在运行时直接产出数据。
    作用:
        约束阶段 4 新 graph 使用的标准字段。messages 使用 LangGraph 追加模式承载对话和 observation。
    为什么需要这个类型?
        旧链路字段分散在 agent/runtime 中；新 graph 需要一个清晰的 state 契约，方便节点、路由和测试共享。
    """

    project_id: str
    repo_path: str
    messages: Annotated[list[dict[str, str]], add_messages]
    next_step: str #用于规划节点的输出，指导后续检索、工具调用或回答
    tool_calls: list[dict[str, object]]

    retrieval_round: int
    tool_round: int
    max_retrieval_rounds: int
    max_tool_rounds: int
    retrieval_top_k: int
    
    answer: str
    status: str
    reason: str
    events: list[dict[str, object]]

    rag_index: object
    tools: object
    tool_executor: object
    chat_model: object


def create_initial_state(
    project_id: str,
    repo_path: str,
    question: str,
    rag_index: object,
    chat_model: object,
    tool_executor:callable
) -> AgentGraphState:
    """
    输入:
        project_id: 项目标识。
        repo_path: 仓库根目录路径。
        question: 用户本轮问题。
    输出:
        AgentGraphState: graph 首次 invoke 时使用的初始状态。
    作用:
        初始化标准 messages、结构化工具计划、流程轮数、回答、状态和事件字段。
    为什么需要这个函数?
        graph 入口需要稳定完整的 state；集中初始化可以避免 runtime 或测试手写字段时遗漏默认值。
    """
    state = AgentGraphState(
        project_id=project_id,
        repo_path=repo_path,
        messages=[{"role": "user", "content": question}],

        retrieval_round=0,
        tool_round=0,
        max_retrieval_rounds=2,
        max_tool_rounds=3,
        retrieval_top_k=5,

        answer="",
        status="running",
        reason="",
        events=[],
        rag_index=rag_index,
        chat_model=chat_model,
        tool_executor=tool_executor
    )
    return state