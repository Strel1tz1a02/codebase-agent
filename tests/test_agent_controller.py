from __future__ import annotations

import unittest

from src.agent.controller import run_agent_loop


class TestAgentController(unittest.TestCase):
    def test_first_step_answer_completes(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "answer", "answer": "入口在 src/main.py"}

        result = run_agent_loop("入口在哪", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "入口在 src/main.py")
        self.assertEqual(result["history"], [])

    def test_tool_then_answer_completes(self) -> None:
        decisions = [
            {
                "decision": "tool",
                "tool_name": "tool_stub_a",
                "arguments": {"query": "entrypoint"},
            },
            {"decision": "answer", "answer": "根据工具结果，入口在 src/main.py"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("入口在哪", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "根据工具结果，入口在 src/main.py")
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["history"][0]["type"], "decision")
        self.assertEqual(result["history"][1]["type"], "tool_result")
        self.assertTrue(result["history"][1]["data"]["ok"])
        self.assertEqual(result["history"][1]["data"]["output"]["echo_args"], {"query": "entrypoint"})

    def test_unknown_tool_is_written_to_history(self) -> None:
        decisions = [
            {
                "decision": "tool",
                "tool_name": "missing_tool",
                "arguments": {},
            },
            {"decision": "answer", "answer": "工具不存在，无法确认"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("入口在哪", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["history"]), 2)
        tool_result = result["history"][1]["data"]
        self.assertFalse(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "missing_tool")
        self.assertEqual(tool_result["error"], "unknown tool: missing_tool")

    def test_invalid_llm_payload_returns_stopped(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "tool", "arguments": {}}

        result = run_agent_loop("入口在哪", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["reason"], "tool_name is required when decision=tool")
        self.assertEqual(result["history"], [])

    def test_max_steps_returns_stopped(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {
                "decision": "tool",
                "tool_name": "tool_stub_a",
                "arguments": {},
            }

        result = run_agent_loop(
            "入口在哪",
            "E:\\projects\\codebase-agent",
            fake_llm,
            max_steps=1,
        )

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["reason"], "max_steps reached")
        self.assertEqual(len(result["history"]), 2)


if __name__ == "__main__":
    unittest.main()
