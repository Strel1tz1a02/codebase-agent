from __future__ import annotations

from langgraph.graph import END

from src.graph.state import AgentGraphState


def route_after_plan(state: AgentGraphState) -> str:
    """
    输入:
        state: plan_next_step 执行后的 AgentGraphState，包含 next_step。
    输出:
        str: retrieve_context、plan_tool_use 或 synthesize_answer。
    作用:
        根据 next_step 选择检索、工具规划或直接回答路径。
    为什么需要这个函数?
        graph 分支逻辑不应写在节点内部；单独路由便于测试和后续扩展更多 action。
    """
    next_step = str(state.get("next_step", "answer"))
    if next_step == "retrieve":
        if int(state.get("retrieval_round", 0)) >= int(state.get("max_retrieval_rounds", 2)):
            return "synthesize_answer"
        return "retrieve_context"
    if next_step == "tool":
        if int(state.get("tool_round", 0)) >= int(state.get("max_tool_rounds", 3)):
            return "synthesize_answer"
        return "plan_tool_use"
    if next_step == "answer":
        return "synthesize_answer"
    return "plan_next_step"


def route_after_retrieval(state: AgentGraphState) -> str:
    """
    输入:
        state: retrieve_context 执行后的 AgentGraphState。
    输出:
        str: 下一步节点名称，固定为 plan_next_step。
    作用:
        检索完成后回到统一规划节点，让 graph 基于 observation 决定下一步。
    为什么需要这个函数?
        ReAct 风格中 RAG 召回也是 observation；召回结束后应该重新规划，而不是固定进入工具或回答。
    """
    return "plan_next_step"


def route_after_tool_plan(state: AgentGraphState) -> str:
    """
    输入:
        state: plan_tool_use 执行后的 AgentGraphState，包含 tool_calls。
    输出:
        str: 下一步节点名称，固定为 execute_tools。
    作用:
        工具规划完成后统一进入工具执行节点。
    为什么需要这个函数?
        plan_tool_use 的结果应由 execute_tools 统一消费，即使 tool_calls 为空也由执行节点产生空结果并回到规划节点。
    """
    return "execute_tools"


def route_after_tool_execution(state: AgentGraphState) -> str:
    """
    输入:
        state: execute_tools 执行后的 AgentGraphState。
    输出:
        str: 下一步节点名称，固定为 plan_next_step。
    作用:
        工具执行完成后回到统一规划节点，让 graph 基于工具结果决定下一步。
    为什么需要这个函数?
        ReAct 风格中工具结果也是 observation；执行结束后应该重新规划，而不是直接生成回答。
    """
    return "plan_next_step"


def route_after_synthesis(state: AgentGraphState) -> str:
    """
    输入:
        state: synthesize_answer 执行后的 AgentGraphState。
    输出:
        str: 下一步节点名称，固定为 validate_answer。
    作用:
        把回答生成结果送入校验节点。
    为什么需要这个函数?
        回答生成和回答校验需要分离，方便后续替换校验规则或加入失败重试路径。
    """
    return "validate_answer"


def route_after_validation(state: AgentGraphState) -> str:
    """
    输入:
        state: validate_answer 执行后的 AgentGraphState。
    输出:
        str: 下一步节点名称，固定为 finish。
    作用:
        校验完成后进入统一结束节点。
    为什么需要这个函数?
        无论校验成功还是失败，都应由 finish 统一记录 graph_finished 事件。
    """
    return "finish"


def route_after_finish(state: AgentGraphState) -> str:
    """
    输入:
        state: finish 执行后的 AgentGraphState。
    输出:
        END: LangGraph 结束标记。
    作用:
        通知 LangGraph workflow 已经结束。
    为什么需要这个函数?
        显式结束路由让测试可以直接验证 graph 的最后一步，而不是依赖 builder 内部边定义。
    """
    return END
