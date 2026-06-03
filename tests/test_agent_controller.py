from __future__ import annotations

import unittest
from pathlib import Path

from src.agent.controller import run_agent_loop


class TestAgentController(unittest.TestCase):
    def test_first_step_answer_completes(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "answer", "answer": "entry is src/main.py"}

        result = run_agent_loop("where is entry", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "entry is src/main.py")
        self.assertEqual(result["history"], [])

    def test_tool_then_answer_completes(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        decisions = [
            {
                "decision": "tool",
                "tool_name": "repo_summary",
                "arguments": {},
            },
            {"decision": "answer", "answer": "entry is src/main.py"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("where is entry", repo_path, fake_llm)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "entry is src/main.py")
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["history"][0]["type"], "decision")
        self.assertEqual(result["history"][1]["type"], "tool_result")
        self.assertTrue(result["history"][1]["data"]["ok"])
        self.assertEqual(result["history"][1]["data"]["tool_name"], "repo_summary")
        self.assertIn("src/main.py", result["history"][1]["data"]["output"]["entry_candidates"])

    def test_repo_path_is_injected_for_every_tool_call(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        decisions = [
            {
                "decision": "tool",
                "tool_name": "read_file",
                "arguments": {"path": "src/main.py"},
            },
            {"decision": "answer", "answer": "done"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("read entry file", repo_path, fake_llm)

        self.assertEqual(result["status"], "completed")
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "read_file")
        self.assertIn("def main()", tool_result["output"]["content"])

    def test_repo_path_is_injected_for_repo_summary_tool(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        decisions = [
            {
                "decision": "tool",
                "tool_name": "repo_summary",
                "arguments": {},
            },
            {"decision": "answer", "answer": "entry is src/main.py"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("where is entry", repo_path, fake_llm)

        self.assertEqual(result["status"], "completed")
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "repo_summary")
        self.assertEqual(tool_result["output"]["repo_path"], repo_path)
        self.assertIn("src/main.py", tool_result["output"]["entry_candidates"])

    def test_repo_path_is_injected_for_read_file_tool(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        decisions = [
            {
                "decision": "tool",
                "tool_name": "read_file",
                "arguments": {"path": "src/main.py"},
            },
            {"decision": "answer", "answer": "main lives in src/main.py"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("read entry file", repo_path, fake_llm)

        self.assertEqual(result["status"], "completed")
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "read_file")
        self.assertEqual(tool_result["output"]["path"], "src/main.py")
        self.assertIn("def main()", tool_result["output"]["content"])

    def test_repo_path_is_injected_for_search_code_tool(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        decisions = [
            {
                "decision": "tool",
                "tool_name": "search_code",
                "arguments": {"keyword": "run_agent_loop"},
            },
            {"decision": "answer", "answer": "run_agent_loop lives in controller.py"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("find run_agent_loop", repo_path, fake_llm)

        self.assertEqual(result["status"], "completed")
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "search_code")
        self.assertEqual(tool_result["output"]["scope"], "src")
        self.assertTrue(
            all(str(match["path"]).startswith("src/") for match in tool_result["output"]["matches"])
        )
        self.assertTrue(
            any(
                match["path"] == "src/agent/controller.py"
                and match["text"] == "def run_agent_loop("
                and isinstance(match["line"], int)
                for match in tool_result["output"]["matches"]
            )
        )

    def test_unknown_tool_is_written_to_history(self) -> None:
        decisions = [
            {
                "decision": "tool",
                "tool_name": "missing_tool",
                "arguments": {},
            },
            {"decision": "answer", "answer": "tool is missing"},
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return decisions.pop(0)

        result = run_agent_loop("where is entry", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["history"]), 2)
        tool_result = result["history"][1]["data"]
        self.assertFalse(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "missing_tool")
        self.assertEqual(tool_result["error"], "unknown tool: missing_tool")

    def test_invalid_llm_payload_returns_stopped(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "tool", "arguments": {}}

        result = run_agent_loop("where is entry", "E:\\projects\\codebase-agent", fake_llm)

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["reason"], "tool_name is required when decision=tool")
        self.assertEqual(result["history"], [])

    def test_max_steps_returns_stopped(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {
                "decision": "tool",
                "tool_name": "repo_summary",
                "arguments": {},
            }

        result = run_agent_loop(
            "where is entry",
            str(Path(__file__).resolve().parent.parent),
            fake_llm,
            max_steps=1,
        )

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["reason"], "max_steps reached")
        self.assertEqual(len(result["history"]), 2)


if __name__ == "__main__":
    unittest.main()
