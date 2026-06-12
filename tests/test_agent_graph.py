from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent.graph import build_agent_graph, run_agent_graph


class TestAgentGraph(unittest.TestCase):
    def test_build_agent_graph_returns_invokable_graph(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "answer", "answer": "entry is src/main.py"}

        graph = build_agent_graph()
        state = {
            "question": "where is entry",
            "repo_path": "E:\\projects\\codebase-agent",
            "allowed_tools": ["repo_summary"],
            "history": [],
            "decision": {},
            "tool_result": {},
            "answer": "",
            "status": "",
            "reason": "",
            "step_count": 0,
            "max_steps": 3,
            "llm_decision_func": fake_llm,
        }

        result = graph.invoke(state)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "entry is src/main.py")

    def test_run_agent_graph_completes_when_llm_returns_answer(self) -> None:
        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            self.assertEqual(context["messages"], [{"role": "user", "content": "where is entry"}])
            return {"decision": "answer", "answer": "entry is src/main.py"}

        result = run_agent_graph(
            question="where is entry",
            repo_path="E:\\projects\\codebase-agent",
            llm_decision_func=fake_llm,
            messages=[{"role": "user", "content": "where is entry"}],
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "entry is src/main.py")
        self.assertEqual(result["history"], [])

    def test_run_agent_graph_executes_tool_then_completes(self) -> None:
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

        result = run_agent_graph(
            question="where is entry",
            repo_path=repo_path,
            llm_decision_func=fake_llm,
            max_steps=3,
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "entry is src/main.py")
        self.assertEqual(len(result["history"]), 2)
        self.assertEqual(result["history"][0]["type"], "decision")
        self.assertEqual(result["history"][1]["type"], "tool_result")
        self.assertTrue(result["history"][1]["data"]["ok"])

    def test_run_agent_graph_stops_when_max_steps_reached(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            return {
                "decision": "tool",
                "tool_name": "repo_summary",
                "arguments": {},
            }

        result = run_agent_graph(
            question="where is entry",
            repo_path=repo_path,
            llm_decision_func=fake_llm,
            max_steps=1,
        )

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["answer"], "")
        self.assertEqual(result["reason"], "max_steps reached")
        self.assertEqual(len(result["history"]), 2)

    def test_run_agent_graph_flows_retrieve_code_context_to_answer(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        fake_hits = [
            {
                "relative_path": "src/rag/retrieval.py",
                "start_line": 12,
                "end_line": 60,
                "content": "def retrieve_relevant_chunks(...):\n    pass\n",
                "score": 0.93,
            }
        ]
        decisions = [
            {
                "decision": "tool",
                "tool_name": "retrieve_code",
                "arguments": {"query": "Where is retrieval implemented?", "top_k": 1},
            },
            {
                "decision": "answer",
                "answer": "Retrieval is implemented in src/rag/retrieval.py [src/rag/retrieval.py:12-60].",
            },
        ]

        def fake_llm(context: dict[str, object]) -> dict[str, object]:
            if context["history"]:
                tool_result = context["history"][-1]["data"]
                self.assertEqual(tool_result["tool_name"], "retrieve_code")
                self.assertEqual(tool_result["output"]["matches"], fake_hits)
            return decisions.pop(0)

        with patch("src.tools.codebase.retrieve_relevant_chunks", return_value=fake_hits):
            result = run_agent_graph(
                question="Where is retrieval implemented?",
                repo_path=repo_path,
                llm_decision_func=fake_llm,
                max_steps=2,
            )

        self.assertEqual(result["status"], "completed")
        self.assertIn("[src/rag/retrieval.py:12-60]", result["answer"])
        self.assertEqual(len(result["history"]), 2)
        tool_result = result["history"][1]["data"]
        self.assertTrue(tool_result["ok"])
        self.assertEqual(tool_result["tool_name"], "retrieve_code")
        self.assertEqual(tool_result["output"]["matches"], fake_hits)


if __name__ == "__main__":
    unittest.main()
