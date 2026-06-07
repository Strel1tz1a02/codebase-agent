from __future__ import annotations

import unittest

from pathlib import Path

from src.agent.nodes import (
    decide_next_action,
    execute_selected_tool,
    route_after_decision,
    route_after_tool,
)


class TestAgentNodes(unittest.TestCase):
    def test_decide_next_action_completes_on_answer_decision(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            self.assertEqual(context["question"], "where is entry")
            self.assertEqual(context["repo_path"], "E:\\projects\\codebase-agent")
            self.assertEqual(context["history"], [])
            self.assertEqual(context["allowed_tools"], ["repo_summary"])
            return {"decision": "answer", "answer": "entry is src/main.py"}

        state = {
            "question": "where is entry",
            "repo_path": "E:\\projects\\codebase-agent",
            "history": [],
            "allowed_tools": ["repo_summary"],
            "llm_decision_func": fake_llm,
        }

        result = decide_next_action(state)

        self.assertEqual(result["decision"], {"decision": "answer", "answer": "entry is src/main.py"})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "entry is src/main.py")
        self.assertEqual(result["reason"], "")

    def test_decide_next_action_stops_on_invalid_decision(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "tool", "arguments": {}}

        state = {
            "question": "where is entry",
            "repo_path": "E:\\projects\\codebase-agent",
            "history": [],
            "allowed_tools": ["repo_summary"],
            "llm_decision_func": fake_llm,
        }

        result = decide_next_action(state)

        self.assertEqual(result["decision"], {"decision": "tool", "arguments": {}})
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["reason"], "tool_name is required when decision=tool")

    def test_execute_selected_tool_writes_result_to_history(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        decision = {
            "decision": "tool",
            "tool_name": "read_file",
            "arguments": {"path": "src/main.py"},
        }
        state = {
            "repo_path": repo_path,
            "history": [],
            "decision": decision,
            "step_count": 0,
        }

        result = execute_selected_tool(state)

        self.assertEqual(result["step_count"], 1)
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["history"][0], {"type": "decision", "data": decision})
        self.assertEqual(result["history"][1]["type"], "tool_result")
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "read_file")
        self.assertIn("def main()", tool_result["output"]["content"])
        self.assertEqual(result["tool_result"], tool_result)

    def test_route_after_decision_returns_end_for_completed_or_stopped_state(self) -> None:
        self.assertEqual(route_after_decision({"status": "completed"}), "end")
        self.assertEqual(route_after_decision({"status": "stopped"}), "end")

    def test_route_after_decision_returns_tool_for_tool_decision(self) -> None:
        state = {
            "decision": {
                "decision": "tool",
                "tool_name": "repo_summary",
                "arguments": {},
            }
        }

        self.assertEqual(route_after_decision(state), "tool")

    def test_route_after_tool_returns_decision_when_under_max_steps(self) -> None:
        state = {
            "step_count": 1,
            "max_steps": 3,
        }

        self.assertEqual(route_after_tool(state), "decision")

    def test_route_after_tool_returns_end_when_max_steps_reached(self) -> None:
        state = {
            "step_count": 3,
            "max_steps": 3,
        }

        self.assertEqual(route_after_tool(state), "end")


if __name__ == "__main__":
    unittest.main()
