from __future__ import annotations

import unittest
from pathlib import Path

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
            return {"decision": "answer", "answer": "entry is src/main.py"}

        result = run_agent_graph(
            question="where is entry",
            repo_path="E:\\projects\\codebase-agent",
            llm_decision_func=fake_llm,
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


if __name__ == "__main__":
    unittest.main()
