from __future__ import annotations

from src.agent.schemas import validate_decision_payload
from src.agent.state import AgentGraphState
from src.agent.tools import execute_tool


def decide_next_action(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，至少需要包含 question、repo_path、history、
        allowed_tools 和 llm_decision_func。
    输出:
        更新后的 AgentGraphState。正常情况下会写入 decision；如果 decision 非法，
        会额外写入 status="stopped"、answer="" 和 reason。
    作用:
        调用已有的 LLM 决策函数，让模型决定下一步是调用工具还是直接回答。
    为什么需要这个函数:
        在 LangGraph 中，一个 node 就是一小步可独立理解的状态转换。
        这个节点先只负责“决策”，不负责执行工具，方便初学阶段拆开学习。
    """
    llm_decision_func = state["llm_decision_func"]
    context = {
        "question": state.get("question", ""),
        "repo_path": state.get("repo_path", ""),
        "messages": state.get("messages", []),
        "history": state.get("history", []),
        "allowed_tools": state.get("allowed_tools", []),
    }

    decision = llm_decision_func(context)
    is_valid, error = validate_decision_payload(decision)

    next_state = dict(state)
    next_state["decision"] = decision
    if not is_valid:
        next_state["status"] = "stopped"
        next_state["answer"] = ""
        next_state["reason"] = error
    elif decision.get("decision") == "answer":
        next_state["status"] = "completed"
        next_state["answer"] = str(decision.get("answer", ""))
        next_state["reason"] = ""

    return next_state


def execute_selected_tool(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，至少需要包含 repo_path、history、decision 和 step_count。
        decision 中应包含 tool_name 和 arguments。
    输出:
        更新后的 AgentGraphState，会写入 tool_result，向 history 追加 decision 和
        tool_result，并让 step_count 加 1。
    作用:
        执行 decide_next_action 选出来的工具，并把工具执行结果保存回 state。
    为什么需要这个函数:
        LangGraph 中工具执行应该是独立节点。这样“模型决策”和“本地工具执行”分开，
        后续调试时可以清楚看到 Agent 是怎么从 decision 走到 tool_result 的。
    """
    decision = dict(state.get("decision", {}))
    arguments = dict(decision.get("arguments", {}))
    if "repo_path" not in arguments:
        arguments["repo_path"] = str(state.get("repo_path", ""))

    history = list(state.get("history", []))
    history.append(
        {
            "type": "decision",
            "data": decision,
        }
    )

    tool_result = execute_tool(
        tool_name=str(decision.get("tool_name", "")),
        arguments=arguments,
    )
    tool_result_dict = tool_result.to_dict()
    history.append(
        {
            "type": "tool_result",
            "data": tool_result_dict,
        }
    )

    next_state = dict(state)
    next_state["history"] = history
    next_state["tool_result"] = tool_result_dict
    next_state["step_count"] = int(state.get("step_count", 0)) + 1
    return next_state


def route_after_decision(state: AgentGraphState) -> str:
    """
    输入:
        state: decide_next_action 执行后的 AgentGraphState。
    输出:
        str: 下一步路由名称，目前只返回 "end" 或 "tool"。
    作用:
        根据当前 state 判断 graph 下一步应该结束，还是进入工具执行节点。
    为什么需要这个函数:
        LangGraph 的 conditional edge 需要一个路由函数。把路由判断单独写出来，
        可以先在不引入 LangGraph 的情况下学习和测试图的分支逻辑。
    """
    status = state.get("status", "")
    if status in {"completed", "stopped"}:
        return "end"

    decision = dict(state.get("decision", {}))
    if decision.get("decision") == "tool":
        return "tool"

    return "end"


def route_after_tool(state: AgentGraphState) -> str:
    """
    输入:
        state: execute_selected_tool 执行后的 AgentGraphState。
    输出:
        str: 下一步路由名称，目前返回 "decision" 或 "end"。
    作用:
        判断工具执行后是否还可以继续回到决策节点，还是因为达到最大步数而结束。
    为什么需要这个函数:
        Agent 不能无限循环调用工具。把 max_steps 判断放在独立路由函数里，
        后续接入 LangGraph conditional edge 时可以直接复用。
    """
    step_count = int(state.get("step_count", 0))
    max_steps = int(state.get("max_steps", 3))

    if step_count >= max_steps:
        return "end"

    return "decision"
