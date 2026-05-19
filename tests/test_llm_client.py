from __future__ import annotations

import unittest

from src.llm.client import ask_llm


class TestLLMClient(unittest.TestCase):
    def test_ask_llm_returns_placeholder_answer(self) -> None:
        answer = ask_llm("这个项目的入口在哪里？")

        self.assertIn("TODO: call LLM", answer)
        self.assertIn("这个项目的入口在哪里？", answer)


if __name__ == "__main__":
    unittest.main()
