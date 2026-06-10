from __future__ import annotations

import unittest
from collections.abc import Callable
from unittest.mock import patch

import httpx

from src.agent.tools import TOOL_REGISTRY
from src.agent.adapter import next_decision
from src.api.app import create_app, create_default_runtime
from src.runtime.memory import SessionMemory
from src.runtime.runtime import AgentRuntime


class TestApiApp(unittest.IsolatedAsyncioTestCase):
    def create_transport(
        self,
        agent_runner: Callable[[dict[str, object]], dict[str, object]] | None = None,
    ) -> httpx.ASGITransport:
        memory = SessionMemory()
        runtime = AgentRuntime(memory=memory, agent_runner=agent_runner)
        return httpx.ASGITransport(app=create_app(runtime=runtime))

    async def test_health_returns_ok(self) -> None:
        transport = self.create_transport()

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    async def test_tools_returns_registered_tool_names(self) -> None:
        transport = self.create_transport()

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/tools")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"tools": list(TOOL_REGISTRY.keys())})

    async def test_create_session_returns_session_snapshot(self) -> None:
        transport = self.create_transport()

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sessions",
                json={"repo_path": "E:\\projects\\codebase-agent"},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["repo_path"], "E:\\projects\\codebase-agent")
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["message_count"], 0)
        self.assertIsInstance(payload["session_id"], str)
        self.assertTrue(payload["session_id"])

    async def test_get_session_returns_messages_and_trace(self) -> None:
        transport = self.create_transport()

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/sessions",
                json={"repo_path": "E:\\projects\\codebase-agent"},
            )
            session_id = create_response.json()["session_id"]
            response = await client.get(f"/sessions/{session_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "session_id": session_id,
                "repo_path": "E:\\projects\\codebase-agent",
                "status": "running",
                "messages": [],
                "trace": [],
            },
        )

    async def test_get_missing_session_returns_404(self) -> None:
        transport = self.create_transport()

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/sessions/missing-session")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "session not found: missing-session"})

    def test_create_default_runtime_uses_graph_agent_runner(self) -> None:
        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            return {"status": "completed", "answer": "ok"}

        calls: list[dict[str, object]] = []

        def fake_build_graph_agent_runner(
            llm_decision_func: Callable[[dict[str, object]], dict[str, object]],
            max_steps: int,
        ) -> Callable[[dict[str, object]], dict[str, object]]:
            calls.append(
                {
                    "llm_decision_func": llm_decision_func,
                    "max_steps": max_steps,
                }
            )
            return fake_runner

        with patch(
            "src.api.app.build_graph_agent_runner",
            side_effect=fake_build_graph_agent_runner,
        ):
            runtime = create_default_runtime()

        self.assertIs(runtime.agent_runner, fake_runner)
        self.assertEqual(
            calls,
            [
                {
                    "llm_decision_func": next_decision,
                    "max_steps": 3,
                }
            ],
        )

    def test_create_app_uses_default_runtime_when_not_injected(self) -> None:
        runtime = AgentRuntime(memory=SessionMemory())

        with patch("src.api.app.create_default_runtime", return_value=runtime):
            app = create_app()

        self.assertIs(app.state.runtime, runtime)

    async def test_ask_returns_runner_answer(self) -> None:
        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            return {
                "status": "completed",
                "answer": "入口在 src/main.py。",
                "history": [],
            }

        transport = self.create_transport(agent_runner=fake_runner)

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/sessions",
                json={"repo_path": "E:\\projects\\codebase-agent"},
            )
            session_id = create_response.json()["session_id"]
            response = await client.post(
                f"/sessions/{session_id}/ask",
                json={"question": "入口在哪？"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "session_id": session_id,
                "status": "completed",
                "question": "入口在哪？",
                "answer": "入口在 src/main.py。",
                "reason": "",
                "message_count": 2,
            },
        )

    async def test_get_session_after_ask_returns_messages_and_trace(self) -> None:
        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            return {
                "status": "completed",
                "answer": "入口在 src/main.py。",
                "history": [],
            }

        transport = self.create_transport(agent_runner=fake_runner)

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/sessions",
                json={"repo_path": "E:\\projects\\codebase-agent"},
            )
            session_id = create_response.json()["session_id"]
            await client.post(
                f"/sessions/{session_id}/ask",
                json={"question": "入口在哪？"},
            )
            response = await client.get(f"/sessions/{session_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "session_id": session_id,
                "repo_path": "E:\\projects\\codebase-agent",
                "status": "completed",
                "messages": [
                    {"role": "user", "content": "入口在哪？"},
                    {"role": "assistant", "content": "入口在 src/main.py。"},
                ],
                "trace": [
                    {
                        "status": "completed",
                        "answer": "入口在 src/main.py。",
                        "reason": "",
                    }
                ],
            },
        )

    async def test_ask_includes_stop_reason(self) -> None:
        def fake_runner(payload: dict[str, object]) -> dict[str, object]:
            return {
                "status": "stopped",
                "answer": "",
                "reason": "max_steps reached",
                "history": [],
            }

        transport = self.create_transport(agent_runner=fake_runner)

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            create_response = await client.post(
                "/sessions",
                json={"repo_path": "E:\\projects\\codebase-agent"},
            )
            session_id = create_response.json()["session_id"]
            response = await client.post(
                f"/sessions/{session_id}/ask",
                json={"question": "入口在哪？"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "stopped")
        self.assertEqual(response.json()["answer"], "")
        self.assertEqual(response.json()["reason"], "max_steps reached")
        self.assertEqual(response.json()["message_count"], 1)

    async def test_ask_missing_session_returns_404(self) -> None:
        transport = self.create_transport()

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/sessions/missing-session/ask",
                json={"question": "入口在哪？"},
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "session not found: missing-session"})


if __name__ == "__main__":
    unittest.main()
