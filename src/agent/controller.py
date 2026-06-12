from __future__ import annotations

from collections.abc import Callable

from src.agent.schemas import AgentContext, validate_decision_payload
from src.tools.registry import TOOL_REGISTRY, execute_tool


def run_agent_loop(
    question: str,
    repo_path: str,
    llm_decision_func: Callable[[dict[str, object]], dict[str, object]],
    max_steps: int = 3,
) -> dict[str, object]:
    """
    输入：
        question：用户问题。
        repo_path：要分析的代码仓库路径。
        llm_decision_func：可注入的 LLM 决策函数，输入 context 字典，输出 decision 字典。
        max_steps：最多循环几轮。
    输出：
        dict：Agent 循环结果，包含 status、answer/reason 和 history。
    作用：
        串起“构造上下文 -> 获取决策 -> 执行工具 -> 写入 history”的最小 Agent 循环。
    设计原因：
        当前阶段先不接真实 LLM 和 CLI，用可注入函数把控制流程单独测通。
    """
    context = AgentContext(
        question=question,
        repo_path=repo_path,
        allowed_tools=list(TOOL_REGISTRY.keys()),
    )

    for _ in range(max_steps): 
        decision = llm_decision_func(context.to_dict())
        is_valid, error = validate_decision_payload(decision)

        if not is_valid:
            return {
                "status": "stopped",
                "answer": "",
                "reason": error,
                "history": context.history,
            }

        if decision["decision"] == "answer":
            return {
                "status": "completed",
                "answer": decision["answer"],
                "history": context.history,
            }

        context.history.append(
            {
                "type": "decision",
                "data": decision,
            }
        )

        arguments = dict(decision["arguments"])
        if "repo_path" not in arguments:
            arguments["repo_path"] = repo_path

        tool_result = execute_tool(
            tool_name=str(decision["tool_name"]),
            arguments=arguments,
        )
        context.history.append(
            {
                "type": "tool_result",
                "data": tool_result.to_dict(),
            }
        )

    return {
        "status": "stopped",
        "answer": "",
        "reason": "max_steps reached",
        "history": context.history,
    }
