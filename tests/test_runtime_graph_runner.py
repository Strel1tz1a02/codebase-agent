from __future__ import annotations

import unittest

from src.runtime.graph_runner import build_graph_agent_runner


class TestRuntimeGraphRunner(unittest.TestCase):
    def test_graph_runner_calls_run_graph_with_runtime_payload(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_llm_decision(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "answer", "answer": "ok"}

        def fake_run_graph(
            question: str,
            repo_path: str,
            llm_decision_func,
            max_steps: int,
            messages: list[dict[str, str]],
        ) -> dict[str, object]:
            calls.append(
                {
                    "question": question,
                    "repo_path": repo_path,
                    "llm_decision_func": llm_decision_func,
                    "max_steps": max_steps,
                    "messages": messages,
                }
            )
            return {
                "status": "completed",
                "answer": "入口在 src/main.py。",
                "history": [],
            }

        runner = build_graph_agent_runner(
            llm_decision_func=fake_llm_decision,
            max_steps=4,
            run_graph_func=fake_run_graph,
        )

        result = runner(
            {
                "question": "入口在哪？",
                "repo_path": "E:\\projects\\codebase-agent",
                "messages": [{"role": "user", "content": "入口在哪？"}],
            }
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "入口在 src/main.py。")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["question"], "入口在哪？")
        self.assertEqual(calls[0]["repo_path"], "E:\\projects\\codebase-agent")
        self.assertIs(calls[0]["llm_decision_func"], fake_llm_decision)
        self.assertEqual(calls[0]["max_steps"], 4)
        self.assertEqual(calls[0]["messages"], [{"role": "user", "content": "入口在哪？"}])

    def test_graph_runner_requires_question_and_repo_path(self) -> None:
        def fake_llm_decision(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "answer", "answer": "ok"}

        runner = build_graph_agent_runner(llm_decision_func=fake_llm_decision)

        with self.assertRaises(ValueError):
            runner({"question": "", "repo_path": "E:\\projects\\codebase-agent"})

        with self.assertRaises(ValueError):
            runner({"question": "入口在哪？", "repo_path": ""})


if __name__ == "__main__":
    unittest.main()
