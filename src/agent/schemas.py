from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AgentContext:
    """
    输入：
        question：用户提出的问题。
        repo_path：要分析的代码仓库路径。
        history：Agent 已经发生过的历史记录。
        allowed_tools：当前允许 LLM 选择的工具名列表。
    输出：
        AgentContext 对象，可以通过 to_dict() 转成字典。
    作用：
        保存 Agent 运行时需要共享的全局上下文。
    设计原因：
        控制器、LLM 调用和工具执行都需要读取这些信息，把它们放在一个上下文对象里更清楚。
    """

    question: str
    repo_path: str
    history: list[dict[str, object]] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "repo_path": self.repo_path,
            "history": self.history,
            "allowed_tools": self.allowed_tools,
        }


@dataclass
class AgentDecision:
    """
    输入：
        decision：LLM 的决策，只能是 tool 或 answer。
        tool_name：decision 为 tool 时要调用的工具名。
        arguments：decision 为 tool 时传给工具的参数。
        answer：decision 为 answer 时返回的最终回答。
    输出：
        AgentDecision 对象，可以通过 to_dict() 转成 LLM 决策字典。
    作用：
        表示 LLM 本轮是要调用工具，还是直接回答用户。
    设计原因：
        控制器只需要根据 decision 做分支，不需要理解复杂协议。
    """

    decision: Literal["tool", "answer"]
    tool_name: str = ""
    arguments: dict[str, object] = field(default_factory=dict) #field(): 用于定义可变的参数 default_factory 用于指定一个工厂函数来生成默认值，这在默认值是可变对象（如列表或字典）时非常有用，可以避免多个实例共享同一个默认对象的问题。
    answer: str = ""

    def to_dict(self) -> dict[str, object]:
        if self.decision == "tool":
            return {
                "decision": "tool",
                "tool_name": self.tool_name,
                "arguments": self.arguments,
            }

        return {
            "decision": "answer",
            "answer": self.answer,
        }


@dataclass
class ToolResult:
    """
    输入：
        ok：工具是否执行成功。
        tool_name：工具名。
        output：工具成功时的输出。
        error：工具失败时的错误信息。
    输出：
        ToolResult 对象，可以通过 to_dict() 转成工具结果字典。
    作用：
        表示一次本地工具执行后的结果。
    设计原因：
        控制器可以把工具结果追加到 history 里，再交给 LLM 继续判断。
    """

    ok: bool
    tool_name: str
    output: dict[str, object] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "output": self.output,
            "error": self.error,
        }


def validate_decision_payload(payload: dict[str, object]) -> tuple[bool, str]:
    """
    输入：
        payload：LLM 返回的决策字典。
    输出：
        tuple[bool, str]：是否有效，以及错误原因。
    作用：
        检查 LLM 返回的是工具调用还是最终回答，并确认必要字段存在。
    设计原因：
        LLM 输出可能缺字段，执行工具前先做简单检查，可以让控制器更稳定。
    """
    decision = payload.get("decision")

    if decision not in ("tool", "answer"):
        return False, "decision must be 'tool' or 'answer'"

    if decision == "tool" and not payload.get("tool_name"):
        return False, "tool_name is required when decision=tool"

    if decision == "tool" and "arguments" not in payload:
        return False, "arguments is required when decision=tool"

    if decision == "answer" and "answer" not in payload:
        return False, "answer is required when decision=answer"

    return True, ""
