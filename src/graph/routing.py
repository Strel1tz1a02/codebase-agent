from __future__ import annotations

from langgraph.graph import END

from src.graph.state import AgentGraphState


def route_after_plan(state: AgentGraphState) -> str:
    """
    输入:
        state: plan_next_step 执行后的 AgentGraphState，包含 next_step。
    输出:
        str: execute_tools、synthesize_answer 或 plan_next_step。
    作用:
        根据 next_step 选择工具执行或直接回答路径，并做轮次上限保护。
        无法识别的规划结果会先有限重试，超过上限后兜底进入回答生成，避免死循环。
    """
    next_step = str(state.get("next_step", "answer"))
    if next_step == "execute_tools":
        if int(state.get("tool_round", 0)) >= int(state.get("max_tool_rounds", 3)):
            return "synthesize_answer"
        return "execute_tools"
    if next_step == "answer":
        return "synthesize_answer"
    if int(state.get("invalid_plan_round", 0)) < int(state.get("max_invalid_plan_rounds", 2)):
        return "plan_next_step"
    return "synthesize_answer"


def route_after_tool_execution(state: AgentGraphState) -> str:
    """工具执行完成后回到统一规划节点，让 graph 基于结果决定下一步。"""
    return "plan_next_step"


def route_after_synthesis(state: AgentGraphState) -> str:
    """回答生成完成后送入校验节点。"""
    return "validate_answer"


def route_after_validation(state: AgentGraphState) -> str:
    """校验完成后进入统一结束节点。"""
    return "finish"


def route_after_finish(state: AgentGraphState) -> str:
    """通知 LangGraph workflow 结束。"""
    return END
