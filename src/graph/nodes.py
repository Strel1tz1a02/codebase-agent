from __future__ import annotations

from src.graph.state import AgentGraphState
from src.rag.retrieval import retrieve_from_index


def prepare_context(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，至少包含 project_id、repo_path 和 messages。
    输出:
        写入 context 并追加 context_prepared 事件后的 AgentGraphState。
    作用:
        从标准 messages 中提取用户问题，并把项目、仓库路径和问题整理成后续节点可复用的上下文。
    为什么需要这个函数?
        graph 的第一步应该只负责准备上下文，避免后续检索、工具和回答节点反复解析 messages。
    """
    next_state = dict(state)
    next_state["context"] = {
        "project_id": state.get("project_id", ""),
        "repo_path": state.get("repo_path", ""),
        "question": _latest_user_question(state),
    }
    return _append_event(next_state, {"type": "context_prepared"})


def plan_next_step(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 step_planner fake 或真实规划器。
    输出:
        写入 next_step 并追加 next_step_planned 事件后的 AgentGraphState。
    作用:
        根据当前问题、检索结果和工具结果规划下一步是检索、工具调用，还是生成回答。
    为什么需要这个函数?
        ReAct 风格流程需要在每次 observation 后重新思考下一步；统一规划节点可以让 RAG 和工具结果都回到同一个决策点。
    """
    next_state = dict(state)
    planner = state.get("step_planner")
    next_step = planner(state) if callable(planner) else "answer"
    next_state["next_step"] = str(next_step)
    return _append_event(
        next_state,
        {"type": "next_step_planned", "next_step": str(next_step)},
    )


def retrieve_context(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 retriever。
    输出:
        写入 retrieval_hits 并追加 context_retrieved 事件后的 AgentGraphState。
    作用:
        根据用户问题和仓库路径获取相关代码片段，供回答生成或工具规划使用。
    为什么需要这个函数?
        RAG 检索应作为独立节点存在，召回数量等检索策略应由 retriever 自己决定，graph 只负责编排。
    """
    next_state = dict(state)
    next_state["retrieval_round"] = int(state.get("retrieval_round", 0)) + 1
    rag_index = state.get("rag_index")
    if rag_index is not None:
        hits = [
            hit.to_dict() if hasattr(hit, "to_dict") else hit# hasattr:是否有这个属性或方法
            for hit in retrieve_from_index(
                rag_index,
                _latest_user_question(state),
                int(state.get("retrieval_top_k", 5)),
            )
        ]
    else:
        hits = []

    next_state["retrieval_hits"] = list(hits)
    return _append_event(
        next_state,
        {"type": "context_retrieved", "hit_count": len(next_state["retrieval_hits"])},
    )


def plan_tool_use(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，可选包含 tool_planner。
    输出:
        写入 tool_calls 并追加 tool_use_planned 事件后的 AgentGraphState。
    作用:
        基于当前上下文、检索结果和问题规划需要执行的工具调用。
    为什么需要这个函数?
        工具规划和工具执行需要分开；这样 graph 可以在执行前检查、记录或跳过空 tool_calls。
    """
    next_state = dict(state)
    planner = state.get("tool_planner")
    tool_calls = planner(state) if callable(planner) else []
    next_state["tool_calls"] = list(tool_calls)
    return _append_event(
        next_state,
        {"type": "tool_use_planned", "call_count": len(next_state["tool_calls"])},
    )


def execute_tools(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，包含 tool_calls，可选包含 tool_executor。
    输出:
        写入 tool_results 并追加 tools_executed 事件后的 AgentGraphState。
    作用:
        顺序执行已经规划好的工具调用，并把结果保存回 state。
    为什么需要这个函数?
        本地工具执行是可观察的副作用步骤，单独成节点后可以独立测试 fake executor，
        也方便后续做权限、错误处理和事件追踪。
    """
    next_state = dict(state)
    executor = state.get("tool_executor")
    results = []
    for tool_call in state.get("tool_calls", []):
        if callable(executor):
            results.append(executor(tool_call, state))
        else:
            results.append(
                {
                    "name": tool_call.get("name", ""),
                    "ok": False,
                    "error": "No tool executor configured.",
                }
            )

    next_state["tool_results"] = results
    return _append_event(
        next_state,
        {"type": "tools_executed", "result_count": len(results)},
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
        回答生成是 graph 的核心收束节点，先支持 fake chat model，后续再接真实模型和 prompt 模板。
    """
    next_state = dict(state)
    chat_model = state.get("chat_model")
    if callable(chat_model):
        answer = chat_model(state)
    else:
        answer = "Graph execution completed."

    next_state["answer"] = str(answer)
    return _append_event(next_state, {"type": "answer_synthesized"})


def validate_answer(state: AgentGraphState) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState，至少包含 answer，可选包含 answer_validator。
    输出:
        写入 status、reason 并追加 answer_validated 事件后的 AgentGraphState。
    作用:
        校验回答是否可接受，成功时标记 completed，失败时标记 failed。
    为什么需要这个函数?
        校验独立成节点后，后续可以加入引用检查、空回答检查或安全规则，而不污染回答生成逻辑。
    """
    next_state = dict(state)
    validator = state.get("answer_validator")
    valid = True
    reason = ""

    if callable(validator):
        validation_result = validator(str(state.get("answer", "")), state)
        if isinstance(validation_result, tuple):
            valid = bool(validation_result[0])
            reason = str(validation_result[1])
        else:
            valid = bool(validation_result)

    next_state["status"] = "completed" if valid else "failed"
    next_state["reason"] = reason
    return _append_event(
        next_state,
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
    next_state = dict(state)
    if not str(next_state.get("status", "")):
        next_state["status"] = "completed"
    return _append_event(
        next_state,
        {"type": "graph_finished", "status": str(next_state.get("status", ""))},
    )


def _latest_user_question(state: AgentGraphState) -> str:
    """
    输入:
        state: 当前 AgentGraphState，包含 messages。
    输出:
        str: 最近一条 user 消息内容；不存在时返回空字符串。
    作用:
        为上下文准备和检索节点提供统一的问题提取逻辑。
    为什么需要这个函数?
        messages 是标准对话结构，集中读取可以避免每个节点重复写倒序查找逻辑。
    """
    for message in reversed(state.get("messages", [])):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def _append_event(
    state: AgentGraphState,
    event: dict[str, object],
) -> AgentGraphState:
    """
    输入:
        state: 当前 AgentGraphState。
        event: 要追加的事件字典。
    输出:
        追加事件后的 AgentGraphState。
    作用:
        以不可变风格复制 state，并把新事件追加到 events 列表末尾。
    为什么需要这个函数?
        graph 节点都需要写事件；集中处理可以保证事件追加方式一致，避免误改原始 state。
    """
    next_state = dict(state)
    next_state["events"] = [*state.get("events", []), event]
    return next_state
