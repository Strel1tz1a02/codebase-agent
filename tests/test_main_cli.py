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
        self.assertIn("### Step 1: Tool Result", output)
        self.assertIn("- OK: False", output)
        mock_configure_llm.assert_called_once_with(
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        mock_run_agent_loop.assert_called_once()

    def test_main_graph_mode_runs_agent_graph_and_prints_result(self) -> None:
        fake_args = Namespace(
            config=".codebase_agent/config.json",
            repo="E:\\projects\\demo_repo",
            ask="鍏ュ彛鍦ㄥ摢閲岋紵",
            ask_mode="graph",
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            build_chunks=False,
            top_k=5,
            reindex=False,
            max_steps=4,
        )
        fake_config = {
            "repo": "E:\\projects\\demo_repo",
            "ask_mode": "graph",
            "llm": {
                "provider": "aliyun",
                "model": "qwen-plus",
                "api_key_env": "CODEBASE_AGENT_API_KEY",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            "rag": {"top_k": 5, "reindex": False},
            "agent": {"max_steps": 4},
        }
        fake_graph_result = {
            "status": "completed",
            "answer": "entry is src/main.py",
            "history": [
                {
                    "type": "decision",
                    "data": {
                        "decision": "tool",
                        "tool_name": "search_code",
                        "arguments": {"keyword": "run_agent_loop", "scope": "src"},
                    },
                },
                {
                    "type": "tool_result",
                    "data": {
                        "ok": True,
                        "tool_name": "search_code",
                        "output": {
                            "matches": [
                                {
                                    "path": "src/agent/controller.py",
                                    "line": 9,
                                    "text": "def run_agent_loop(",
                                },
                                {
                                    "path": "src/main.py",
                                    "line": 15,
                                    "text": "from src.agent.controller import run_agent_loop",
                                }
                            ]
                        },
                        "error": "",
                    },
                },
            ],
        }

        with patch("src.main.parse_args", return_value=fake_args), patch(
            "src.main.load_app_config", return_value=fake_config
        ), patch(
            "src.main.run_agent_graph", return_value=fake_graph_result
        ) as mock_run_agent_graph, patch("src.main.configure_llm") as mock_configure_llm, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as fake_stdout:
            main()

        output = fake_stdout.getvalue()
        self.assertIn("## Agent Status", output)
        self.assertIn("completed", output)
        self.assertIn("entry is src/main.py", output)
        self.assertIn("## History", output)
        self.assertIn("### Step 1: Decision", output)
        self.assertIn("- Tool: search_code", output)
        self.assertIn("- Arguments: keyword=run_agent_loop, scope=src", output)
        self.assertIn("### Step 1: Tool Result", output)
        self.assertIn("- OK: True", output)
        self.assertIn("- Matches: 2", output)
        self.assertIn("  1. src/agent/controller.py:9 def run_agent_loop(", output)
        self.assertIn("  2. src/main.py:15 from src.agent.controller import run_agent_loop", output)
        mock_configure_llm.assert_called_once_with(
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        mock_run_agent_graph.assert_called_once()

    def test_main_graph_mode_prints_retrieve_code_history_matches(self) -> None:
        fake_args = Namespace(
            config=".codebase_agent/config.json",
            repo="E:\\projects\\demo_repo",
            ask="How does retrieval work?",
            ask_mode="graph",
            provider="aliyun",
            model="qwen-plus",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            build_chunks=False,
            top_k=5,
            reindex=False,
            max_steps=4,
        )
        fake_config = {
            "repo": "E:\\projects\\demo_repo",
            "ask_mode": "graph",
            "llm": {
                "provider": "aliyun",
                "model": "qwen-plus",
                "api_key_env": "CODEBASE_AGENT_API_KEY",
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            "rag": {"top_k": 5, "reindex": False},
            "agent": {"max_steps": 4},
        }
        fake_graph_result = {
            "status": "completed",
            "answer": "RAG lives in retrieval.py [src/rag/retrieval.py:12-60].",
            "history": [
                {
                    "type": "decision",
                    "data": {
                        "decision": "tool",
                        "tool_name": "retrieve_code",
                        "arguments": {"query": "retrieval workflow", "top_k": 1},
                    },
                },
                {
                    "type": "tool_result",
                    "data": {
                        "ok": True,
                        "tool_name": "retrieve_code",
                        "output": {
                            "matches": [
                                {
                                    "relative_path": "src/rag/retrieval.py",
                                    "start_line": 12,
                                    "end_line": 60,
                                    "content": "def retrieve_relevant_chunks(...):\n    pass\n",
                                    "score": 0.93,
                                }
                            ]
                        },
                        "error": "",
                    },
                },
            ],
        }

        with patch("src.main.parse_args", return_value=fake_args), patch(
            "src.main.load_app_config", return_value=fake_config
        ), patch(
            "src.main.run_agent_graph", return_value=fake_graph_result
        ), patch("src.main.configure_llm"), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as fake_stdout:
            main()

        output = fake_stdout.getvalue()
        self.assertIn("- Matches: 1", output)
        self.assertIn(
            "  1. src/rag/retrieval.py:12-60 score=0.930000 def retrieve_relevant_chunks(...):",
            output,
        )


if __name__ == "__main__":
    unittest.main()
