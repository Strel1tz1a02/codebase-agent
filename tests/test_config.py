from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from src.config import get_llm_config, load_app_config, merge_cli_args


class TestConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="config_test_"))
        self.config_path = self.temp_dir / "config.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.environ.pop("CODEBASE_AGENT_API_KEY", None)

    def test_load_app_config_reads_json_object(self) -> None:
        self.config_path.write_text('{"repo":"E:\\\\projects\\\\demo"}', encoding="utf-8")
        config = load_app_config(str(self.config_path))
        self.assertEqual(config["repo"], "E:\\projects\\demo")

    def test_merge_cli_args_overrides_config(self) -> None:
        config = {
            "repo": "E:\\projects\\old",
            "ask_mode": "basic",
            "llm": {"provider": "aliyun", "model": "qwen-turbo", "base_url": ""},
            "rag": {"top_k": 3, "reindex": False},
            "agent": {"max_steps": 2},
        }
        args = Namespace(
            repo="E:\\projects\\new",
            ask_mode="rag",
            provider="deepseek",
            model="deepseek-chat",
            api_key=None,
            base_url="https://example.com/v1",
            top_k=8,
            reindex=True,
            max_steps=5,
        )
        merged = merge_cli_args(config, args)
        self.assertEqual(merged["repo"], "E:\\projects\\new")
        self.assertEqual(merged["ask_mode"], "rag")
        self.assertEqual(merged["llm"]["provider"], "deepseek")
        self.assertEqual(merged["llm"]["model"], "deepseek-chat")
        self.assertEqual(merged["llm"]["base_url"], "https://example.com/v1")
        self.assertEqual(merged["rag"]["top_k"], 8)
        self.assertTrue(merged["rag"]["reindex"])
        self.assertEqual(merged["agent"]["max_steps"], 5)

    def test_get_llm_config_reads_api_key_from_env(self) -> None:
        os.environ["CODEBASE_AGENT_API_KEY"] = "env-key"
        config = {
            "llm": {
                "provider": "aliyun",
                "model": "qwen-plus",
                "api_key_env": "CODEBASE_AGENT_API_KEY",
                "base_url": "",
            }
        }
        llm = get_llm_config(config)
        self.assertEqual(llm["api_key"], "env-key")
        self.assertEqual(llm["provider"], "aliyun")
        self.assertEqual(llm["model"], "qwen-plus")


if __name__ == "__main__":
    unittest.main()
