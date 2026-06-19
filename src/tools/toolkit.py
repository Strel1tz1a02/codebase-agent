from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from langchain_core.tools import BaseTool

from src.tools.codebase import repo_summary_tool, retrieve_code_tool, search_code_tool
from src.tools.filesystem import read_file_tool
from src.tools.history import READ_HISTORY_RUN_TOOL_NAME, read_history_run, read_history_run_tool


@dataclass
class ToolContext:
    session: object | None = None
    project: object | None = None
    repo_path: str = ""


@dataclass
class ToolResult:
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

    def __str__(self) -> str:
        if self.ok:
            return json.dumps(self.output, ensure_ascii=False, default=str)
        return f"工具 {self.tool_name} 执行失败: {self.error}"


DEFAULT_TOOLS: list[BaseTool] = [
    repo_summary_tool,
    read_file_tool,
    search_code_tool,
    retrieve_code_tool,
    read_history_run_tool,
]

TOOL_REGISTRY: dict[str, BaseTool | Callable[[dict[str, object]], dict[str, object]]] = {
    tool.name: tool for tool in DEFAULT_TOOLS
}


def format_tool_descriptions() -> str:
    lines = ["可用工具：", ""]
    for tool in DEFAULT_TOOLS:
        desc = str(getattr(tool, "description", "")).strip()
        if desc:
            lines.append(f"  {tool.name}: {desc}")
            lines.append("")
    return "\n".join(lines)


def execute_tool(
    tool_name: str,
    arguments: dict[str, object],
    context: ToolContext | None = None,
) -> ToolResult:
    if tool_name == READ_HISTORY_RUN_TOOL_NAME:
        if context is None or context.session is None:
            return ToolResult(
                ok=False,
                tool_name=tool_name,
                output={},
                error="session context required",
            )
        try:
            output = read_history_run(context.session, str(arguments.get("run_id", "")))  # type: ignore[arg-type]
        except Exception as exc:
            return ToolResult(
                ok=False,
                tool_name=tool_name,
                output={},
                error=str(exc),
            )
        return ToolResult(ok=True, tool_name=tool_name, output=output, error="")

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
