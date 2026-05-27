from __future__ import annotations

import unittest
from unittest.mock import patch

from src.agent.adapter import build_prompt, next_decision, parse_llm


class TestAgentAdapter(unittest.TestCase):
    def test_build_prompt_contains_context_and_json_contract(self) -> None:
        context = {
            "question": "入口在哪",
            "repo_path": "E:\\projects\\codebase-agent",
            "history": [],
            "allowed_tools": ["tool_stub_a", "tool_stub_b"],
        }

        prompt = build_prompt(context)

        self.assertIn('"decision":"tool"', prompt)
        self.assertIn('"decision":"answer"', prompt)
        self.assertIn('"question": "入口在哪"', prompt)
        self.assertIn('"allowed_tools": [', prompt)

    def test_parse_llm_supports_plain_json(self) -> None:
        payload = parse_llm('{"decision":"answer","answer":"ok"}')
        self.assertEqual(payload["decision"], "answer")
        self.assertEqual(payload["answer"], "ok")

    def test_parse_llm_supports_json_fenced_block(self) -> None:
        text = '```json\n{"decision":"tool","tool_name":"tool_stub_a","arguments":{}}\n```'
        payload = parse_llm(text)
        self.assertEqual(payload["decision"], "tool")
        self.assertEqual(payload["tool_name"], "tool_stub_a")

    def test_parse_llm_returns_invalid_payload_on_parse_failure(self) -> None:
        payload = parse_llm("not json")
        self.assertEqual(payload["decision"], "invalid")
        self.assertIn("json parse failed", str(payload["error"]))

    def test_next_decision_calls_ask_llm_and_parses(self) -> None:
        context = {
            "question": "入口在哪",
            "repo_path": "E:\\projects\\codebase-agent",
            "history": [],
            "allowed_tools": ["tool_stub_a"],
        }

        with patch(
            "src.agent.adapter.ask_llm",
            return_value='{"decision":"answer","answer":"入口在 src/main.py"}',
        ) as mock_ask_llm:
            payload = next_decision(context)

        self.assertEqual(payload["decision"], "answer")
        self.assertEqual(payload["answer"], "入口在 src/main.py")
        mock_ask_llm.assert_called_once()


if __name__ == "__main__":
    unittest.main()
