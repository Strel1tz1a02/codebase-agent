from __future__ import annotations

import io
import unittest
from argparse import Namespace
from unittest.mock import patch

from src.main import main


class TestMainCLI(unittest.TestCase):
    def test_main_ask_mode_prints_prompt_answer_and_used_files(self) -> None:
        fake_args = Namespace(
            config=".codebase_agent/config.json",
            repo="E:\\projects\\demo_repo",
            ask="入口在哪里？",
            ask_mode="basic",
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            build_chunks=False,
            top_k=5,
            reindex=False,
            max_steps=None,
        )
        fake_config = {
            "repo": "E:\\projects\\demo_repo",
            "ask_mode": "basic",
            "llm": {
                "provider": "aliyun",
                "model": "qwen-plus",
                "api_key_env": "CODEBASE_AGENT_API_KEY",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            "rag": {"top_k": 5, "reindex": False},
            "agent": {"max_steps": 3},
        }
        fake_scan_result = {"repo_path": "E:\\projects\\demo_repo"}
        fake_qa_result = {
            "prompt": "这是测试 prompt",
            "answer": "这是测试回答",
            "used_files": [
                "E:\\projects\\demo_repo\\README.md",
                "E:\\projects\\demo_repo\\src\\main.py",
            ],
        }

        with patch("src.main.parse_args", return_value=fake_args), patch(
            "src.main.load_app_config", return_value=fake_config
        ), patch(
            "src.main.run_v1_scan", return_value=fake_scan_result
        ), patch("src.main.answer_project_question", return_value=fake_qa_result), patch(
            "src.main.configure_llm"
        ) as mock_configure_llm, patch("sys.stdout", new_callable=io.StringIO) as fake_stdout:
            main()

        output = fake_stdout.getvalue()
        self.assertIn("## Prompt", output)
        self.assertIn("这是测试 prompt", output)
        self.assertIn("## 回答", output)
        self.assertIn("这是测试回答", output)
        self.assertIn("## 使用的上下文文件", output)
        self.assertIn("E:\\projects\\demo_repo\\README.md", output)
        self.assertIn("E:\\projects\\demo_repo\\src\\main.py", output)
        mock_configure_llm.assert_called_once_with(
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

    def test_main_agent_mode_runs_agent_loop_and_prints_result(self) -> None:
        fake_args = Namespace(
            config=".codebase_agent/config.json",
            repo="E:\\projects\\demo_repo",
            ask="入口在哪里？",
            ask_mode="agent",
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            build_chunks=False,
            top_k=5,
            reindex=False,
            max_steps=3,
        )
        fake_config = {
            "repo": "E:\\projects\\demo_repo",
            "ask_mode": "agent",
            "llm": {
                "provider": "aliyun",
                "model": "qwen-plus",
                "api_key_env": "CODEBASE_AGENT_API_KEY",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            "rag": {"top_k": 5, "reindex": False},
            "agent": {"max_steps": 3},
        }
        fake_agent_result = {
            "status": "stopped",
            "answer": "",
            "reason": "max_steps reached",
            "history": [{"type": "tool_result", "data": {"ok": False}}],
        }

        with patch("src.main.parse_args", return_value=fake_args), patch(
            "src.main.load_app_config", return_value=fake_config
        ), patch(
            "src.main.run_agent_loop", return_value=fake_agent_result
        ) as mock_run_agent_loop, patch("src.main.configure_llm") as mock_configure_llm, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as fake_stdout:
            main()

        output = fake_stdout.getvalue()
        self.assertIn("## Agent Status", output)
        self.assertIn("stopped", output)
        self.assertIn("## 回答", output)
        self.assertIn("## 停止原因", output)
        self.assertIn("max_steps reached", output)
        self.assertIn("## History", output)
        self.assertIn("tool_result", output)
        mock_configure_llm.assert_called_once_with(
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        mock_run_agent_loop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
