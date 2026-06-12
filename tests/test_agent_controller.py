from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent.controller import run_agent_loop
from src.agent.adapter import build_prompt


class TestAgentController(unittest.TestCase):
    def test_agent_prompt_describes_retrieve_code_and_citation_rule(self) -> None:
        prompt = build_prompt(
            {
                "question": "How does the agent execute tools?",
                "repo_path": "E:\\projects\\codebase-agent",
                "history": [],
                "allowed_tools": ["repo_summary", "read_file", "search_code", "retrieve_code"],
            }
        )

        self.assertIn('"tool_name":"retrieve_code"', prompt)
        self.assertIn("基于 RAG 索引做语义检索", prompt)
        self.assertIn("[relative_path:start_line-end_line]", prompt)

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

    def test_retrieve_code_result_is_written_to_history(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        fake_hits = [
            {
                "relative_path": "src/agent/tools.py",
                "start_line": 120,
                "end_line": 150,
                "content": "def retrieve_code(...):\n    pass\n",
                "score": 0.88,
            }
        ]
        decisions = [
            {
                "decision": "tool",
                "tool_name": "retrieve_code",
                "arguments": {"query": "How is RAG exposed as a tool?", "top_k": 1},
            },
            {
                "decision": "answer",
                "answer": "RAG is exposed through retrieve_code [src/agent/tools.py:120-150].",
            },
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            if context["history"]:
                tool_result = context["history"][-1]["data"]
                self.assertEqual(tool_result["tool_name"], "retrieve_code")
                self.assertEqual(tool_result["output"]["matches"], fake_hits)
            return decisions.pop(0)

        with patch("src.tools.codebase.retrieve_relevant_chunks", return_value=fake_hits):
            result = run_agent_loop(
                "How is RAG exposed as a tool?",
                repo_path,
                fake_llm,
                max_steps=2,
            )

        self.assertEqual(result["status"], "completed")
        self.assertIn("[src/agent/tools.py:120-150]", result["answer"])
        self.assertEqual(len(result["history"]), 2)
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "retrieve_code")
        self.assertEqual(tool_result["output"]["matches"], fake_hits)

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
