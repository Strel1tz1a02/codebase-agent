from __future__ import annotations

import unittest

from src.runtime.runtime import AgentRuntime
from src.runtime.memory import SessionMemory
from src.runtime.graph_runner import build_graph_agent_runner


class MemoryThatRejectsAppend(SessionMemory):
    def append_message(self, session_id: str, role: str, content: str):
        raise AssertionError("runtime should append messages through Session")

    def append_trace_event(self, session_id: str, payload: dict[str, object]):
        raise AssertionError("runtime should append trace through Session")


class TestAgentRuntime(unittest.TestCase):
    def test_create_session_delegates_to_store(self) -> None:
        memory = SessionMemory()
        runtime = AgentRuntime(memory=memory)

        session = runtime.create_session("E:\\projects\\codebase-agent")

        loaded = memory.get_session(session.session_id)
        self.assertIs(loaded, session)
        self.assertEqual(session.repo_path, "E:\\projects\\codebase-agent")
        self.assertEqual(session.messages, [])

    def test_ask_appends_user_message_to_session(self) -> None:
        memory = SessionMemory()
        runtime = AgentRuntime(memory=memory)
        session = runtime.create_session("E:\\projects\\codebase-agent")

        result = runtime.ask(session.session_id, "入口在哪？")

        self.assertEqual(result["session_id"], session.session_id)
        self.assertEqual(result["status"], "running")
        self.assertEqual(result["question"], "入口在哪？")
        self.assertEqual(result["message_count"], 1)
        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.messages[0].role, "user")
        self.assertEqual(session.messages[0].content, "入口在哪？")

    def test_ask_calls_agent_runner_and_appends_assistant_answer(self) -> None:
        runner_calls: list[dict[str, object]] = []

        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            runner_calls.append(payload)
            return {
                "status": "completed",
                "answer": "入口在 src/main.py。",
                "history": [{"type": "decision", "data": {"decision": "answer"}}],
            }

        memory = SessionMemory()
        runtime = AgentRuntime(memory=memory, agent_runner=fake_runner)
        session = runtime.create_session("E:\\projects\\codebase-agent")

        result = runtime.ask(session.session_id, "入口在哪？")

        self.assertEqual(len(runner_calls), 1)
        self.assertEqual(runner_calls[0]["question"], "入口在哪？")
        self.assertEqual(runner_calls[0]["repo_path"], "E:\\projects\\codebase-agent")
        self.assertEqual(runner_calls[0]["messages"], [{"role": "user", "content": "入口在哪？"}])

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "入口在 src/main.py。")
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertEqual(session.messages[1].content, "入口在 src/main.py。")
        self.assertEqual(len(session.trace), 1)
        self.assertEqual(session.trace[0].payload["status"], "completed")
        self.assertNotIn("history", session.trace[0].payload)

    def test_ask_records_stop_reason_from_agent_runner(self) -> None:
        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            return {
                "status": "stopped",
                "answer": "",
                "reason": "max_steps reached",
                "history": [],
            }

        runtime = AgentRuntime(
            memory=SessionMemory(),
            agent_runner=fake_runner,
        )
        session = runtime.create_session("E:\\projects\\codebase-agent")

        result = runtime.ask(session.session_id, "入口在哪？")

        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["reason"], "max_steps reached")
        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.trace[0].payload["reason"], "max_steps reached")
        self.assertNotIn("history", session.trace[0].payload)

    def test_ask_updates_session_directly_after_loading_from_memory(self) -> None:
        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            return {
                "status": "completed",
                "answer": "入口在 src/main.py。",
                "history": [],
            }

        memory = MemoryThatRejectsAppend()
        runtime = AgentRuntime(memory=memory, agent_runner=fake_runner)
        session = runtime.create_session("E:\\projects\\codebase-agent")

        result = runtime.ask(session.session_id, "入口在哪？")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(session.messages), 2)
        self.assertEqual(session.messages[0].role, "user")
        self.assertEqual(session.messages[1].role, "assistant")
        self.assertEqual(len(session.trace), 1)

    def test_ask_can_use_graph_agent_runner_adapter(self) -> None:
        def fake_llm_decision(context: dict[str, object]) -> dict[str, object]:
            return {"decision": "answer", "answer": "ok"}

        def fake_run_graph(
            question: str,
            repo_path: str,
            llm_decision_func,
            max_steps: int,
            messages: list[dict[str, str]],
        ) -> dict[str, object]:
            return {
                "status": "completed",
                "answer": f"{question} -> {repo_path}",
                "history": [],
            }

        runtime = AgentRuntime(
            memory=SessionMemory(),
            agent_runner=build_graph_agent_runner(
                llm_decision_func=fake_llm_decision,
                max_steps=2,
                run_graph_func=fake_run_graph,
            ),
        )
        session = runtime.create_session("E:\\projects\\codebase-agent")

        result = runtime.ask(session.session_id, "入口在哪？")

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "入口在哪？ -> E:\\projects\\codebase-agent")
        self.assertEqual(session.messages[-1].role, "assistant")
        self.assertEqual(session.messages[-1].content, "入口在哪？ -> E:\\projects\\codebase-agent")

    def test_ask_raises_for_unknown_session(self) -> None:
        runtime = AgentRuntime(memory=SessionMemory())

        with self.assertRaises(KeyError):
            runtime.ask("missing-session", "入口在哪？")


if __name__ == "__main__":
    unittest.main()
