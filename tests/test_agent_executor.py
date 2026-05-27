from __future__ import annotations

import unittest

from src.agent.executor import TOOL_REGISTRY, execute_tool


class TestAgentExecutor(unittest.TestCase):
    def test_registered_tool_executes_successfully(self) -> None:
        result = execute_tool("tool_stub_a", {})

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "tool_stub_a")
        self.assertEqual(result.error, "")
        self.assertEqual(result.output["tool"], "tool_stub_a")

    def test_arguments_are_echoed_unchanged(self) -> None:
        arguments = {"query": "entrypoint", "limit": 3}

        result = execute_tool("tool_stub_a", arguments)

        self.assertTrue(result.ok)
        self.assertEqual(result.output["echo_args"], arguments)

    def test_unknown_tool_returns_failed_result(self) -> None:
        result = execute_tool("missing_tool", {})

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "missing_tool")
        self.assertEqual(result.output, {})
        self.assertEqual(result.error, "unknown tool: missing_tool")

    def test_tool_exception_is_wrapped_as_failed_result(self) -> None:
        def broken_tool(arguments: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("boom")

        TOOL_REGISTRY["broken_tool"] = broken_tool
        try:
            result = execute_tool("broken_tool", {"x": 1})
        finally:
            del TOOL_REGISTRY["broken_tool"]

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "broken_tool")
        self.assertEqual(result.output, {})
        self.assertEqual(result.error, "boom")


if __name__ == "__main__":
    unittest.main()
