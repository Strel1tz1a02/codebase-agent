from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from langchain_core.tools import BaseTool

from src.tools.codebase import repo_summary_tool, retrieve_code_tool, search_code_tool
from src.tools.filesystem import read_file_tool


@dataclass
class ToolResult:
    """
    输入：
        ok：工具是否执行成功。
        tool_name：工具名。
        output：工具成功时的结构化输出。
        error：工具失败时的错误信息。
    输出：
        ToolResult：工具执行结果对象。
    作用：
        统一描述一次工具调用的成功或失败。
    设计原因：
        工具层不应该依赖旧 agent 包；结果对象放在 registry 中可以避免循环 import。
    """

    ok: bool
    tool_name: str
    output: dict[str, object] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        """
        输入：
            self：当前 ToolResult 对象。
        输出：
            dict：可写入 Agent history 的结构化结果。
        作用：
            把 dataclass 转成普通字典。
        设计原因：
            Runtime、Graph 和测试都更容易消费普通 dict。
        """
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "output": self.output,
            "error": self.error,
        }


DEFAULT_TOOLS: list[BaseTool] = [
    repo_summary_tool,
    read_file_tool,
    search_code_tool,
    retrieve_code_tool,
]

TOOL_REGISTRY: dict[str, BaseTool | Callable[[dict[str, object]], dict[str, object]]] = {
    tool.name: tool for tool in DEFAULT_TOOLS
}


def build_tools() -> list[BaseTool]:
    """
    输入：
        无。
    输出：
        list[BaseTool]：LangChain-compatible 工具列表。
    作用：
        统一返回 codebase-agent 当前可用的工具。
    设计原因：
        Graph、API 和 CLI 后续可以从同一个 registry 获取工具，避免多个入口维护多份工具清单。
    """
    return DEFAULT_TOOLS.copy()


def execute_tool(tool_name: str, arguments: dict[str, object]) -> ToolResult:
    """
    输入：
        tool_name：要执行的工具名。
        arguments：工具参数字典。
    输出：
        ToolResult：统一的工具执行结果。
    作用：
        根据工具名从 registry 找到 LangChain tool 并执行。
    设计原因：
        旧 controller 和 graph 仍需要 ToolResult 结构；工具实现已经迁移到新的 LangChain 工具层。
    """
    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolResult(
            ok=False,
            tool_name=tool_name,
            output={},
            error=f"unknown tool: {tool_name}",
        )

    try:
        if isinstance(tool, BaseTool):
            output = tool.invoke(arguments)
        else:
            output = tool(arguments)
    except Exception as exc:
        return ToolResult(
            ok=False,
            tool_name=tool_name,
            output={},
            error=str(exc),
        )

    if not isinstance(output, dict):
        output = {"result": output}

    return ToolResult(
        ok=True,
        tool_name=tool_name,
        output=output,
        error="",
    )
