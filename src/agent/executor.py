from __future__ import annotations

from src.agent.schemas import ToolResult


def tool_stub_a(arguments: dict[str, object]) -> dict[str, object]:
    """
    输入：
        arguments：工具参数字典。
    输出：
        dict：固定 mock 结果，并回显 arguments。
    作用：
        提供一个可执行的假工具，用来验证 executor 流程。
    设计原因：
        当前阶段先不接真实代码分析工具，用 stub 可以单独测试工具执行分支。
    """
    return {
        "tool": "tool_stub_a",
        "echo_args": arguments,
    }


def tool_stub_b(arguments: dict[str, object]) -> dict[str, object]:
    """
    输入：
        arguments：工具参数字典。
    输出：
        dict：固定 mock 结果，并回显 arguments。
    作用：
        提供第二个假工具，证明 registry 可以管理多个工具。
    设计原因：
        Agent 后续会有多个工具，先用两个 stub 练习按名称分发。
    """
    return {
        "tool": "tool_stub_b",
        "echo_args": arguments,
    }


TOOL_REGISTRY = {
    "tool_stub_a": tool_stub_a,
    "tool_stub_b": tool_stub_b,
}


def execute_tool(tool_name: str, arguments: dict[str, object]) -> ToolResult:
    """
    输入：
        tool_name：要执行的工具名。
        arguments：传给工具的参数字典。
    输出：
        ToolResult：统一的工具执行结果。
    作用：
        根据 tool_name 从 TOOL_REGISTRY 找工具，执行后包装成 ToolResult。
    设计原因：
        控制器只需要调用 execute_tool，不需要知道每个工具函数如何查找和处理异常。
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
        output = tool(arguments)
    except Exception as exc:
        return ToolResult(
            ok=False,
            tool_name=tool_name,
            output={},
            error=str(exc),
        )

    return ToolResult(
        ok=True,
        tool_name=tool_name,
        output=output,
        error="",
    )
