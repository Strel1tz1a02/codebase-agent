from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypedDict


class AgentGraphState(TypedDict, total=False):# typedDict 允许我们定义一个字典类型，其中的键和值都有特定的类型。total=False 表示这个字典中的键是可选的。
    """
    输入:
        LangGraph 每个节点共享和更新的状态字典。
    输出:
        AgentGraphState 类型本身不产生运行时输出，用于约束 state 字段。
    作用:
        描述 V4 graph 模式在节点之间传递哪些信息。
    为什么需要这个类型:
        V3 的变量散落在 Python for loop 中；V4 需要一个显式 state，方便映射到
        LangGraph 的 StateGraph。
    """

    question: str
    repo_path: str
    allowed_tools: list[str]
    history: list[dict[str, object]]
    decision: dict[str, object]
    tool_result: dict[str, object]
    answer: str
    status: Literal["", "completed", "stopped"]#literal 用于指定一个变量只能取特定的值。在这个例子中，status 字段只能是 "", "completed" 或 "stopped" 这三个字符串中的一个。
    reason: str
    step_count: int
    max_steps: int
    llm_decision_func: Callable[[dict[str, object]], dict[str, object]]# Callable 是一个类型提示，表示 llm_decision_func 是一个可调用对象（如函数），它接受一个 dict[str, object] 类型的参数，并返回一个 dict[str, object] 类型的结果。
