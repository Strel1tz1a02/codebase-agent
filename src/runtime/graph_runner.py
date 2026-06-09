from __future__ import annotations

from collections.abc import Callable

from src.agent.graph import run_agent_graph


GraphRunFunc = Callable[
    [
        str,
        str,
        Callable[[dict[str, object]], dict[str, object]],
        int,
        list[dict[str, str]],
    ],
    dict[str, object],
]


def build_graph_agent_runner(
    llm_decision_func: Callable[[dict[str, object]], dict[str, object]],
    max_steps: int = 3,
    run_graph_func: GraphRunFunc = run_agent_graph,
) -> Callable[[dict[str, object]], dict[str, object]]:
    """
    输入：
        llm_decision_func：LangGraph Agent 使用的 LLM 决策函数。
        max_steps：最大工具调用步数。
        run_graph_func：实际执行 graph 的函数，默认是 run_agent_graph。
    输出：
        Callable：可传给 AgentRuntime 的 agent_runner。
    作用：
        把 Runtime payload 适配成 run_agent_graph 的参数。
    设计原因：
        AgentRuntime 不应该直接依赖 LangGraph 函数签名，中间加一层适配更清楚。
    """

    def runner(payload: dict[str, object]) -> dict[str, object]:
        """
        输入：
            payload：Runtime 传入的本轮运行上下文，包含 question、repo_path、messages。
        输出：
            dict：graph runner 的执行结果。
        作用：
            校验 Runtime payload，并调用 LangGraph Agent。
        设计原因：
            Runtime 使用统一 agent_runner 协议；LangGraph 细节集中在这一层。
        """
        question = str(payload.get("question", "")).strip()
        repo_path = str(payload.get("repo_path", "")).strip()
        if not question:
            raise ValueError("question is required")
        if not repo_path:
            raise ValueError("repo_path is required")

        return run_graph_func(
            question,
            repo_path,
            llm_decision_func,
            max_steps,
            list(payload.get("messages", [])),  # type: ignore[arg-type]
        )

    return runner
