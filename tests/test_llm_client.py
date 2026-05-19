from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.llm.client import (
    PROVIDER_MODEL_REGISTRY,
    REGISTERED_PROVIDERS,
    ask_llm,
    configure_llm,
)


class TestLLMClient(unittest.TestCase):
    def setUp(self) -> None:
        configure_llm()

    def test_ask_llm_returns_message_when_provider_missing(self) -> None:
        answer = ask_llm("项目入口在哪里？")
        self.assertIn("--provider", answer)

    def test_registered_providers_contains_mainstream_domestic(self) -> None:
        self.assertIn("aliyun", REGISTERED_PROVIDERS)
        self.assertIn("deepseek", REGISTERED_PROVIDERS)
        self.assertIn("siliconflow", REGISTERED_PROVIDERS)
        self.assertIn("zhipu", REGISTERED_PROVIDERS)
        self.assertIn("baidu", REGISTERED_PROVIDERS)

    def test_provider_model_registry_contains_free_mainstream_models(self) -> None:
        self.assertIn("qwen-plus", PROVIDER_MODEL_REGISTRY["aliyun"])
        self.assertIn("deepseek-chat", PROVIDER_MODEL_REGISTRY["deepseek"])
        self.assertIn("glm-4-flash", PROVIDER_MODEL_REGISTRY["zhipu"])
        self.assertIn("deepseek-ai/DeepSeek-V3", PROVIDER_MODEL_REGISTRY["siliconflow"])

    def test_ask_llm_returns_message_when_api_key_missing(self) -> None:
        configure_llm(provider="aliyun", model="qwen-plus")
        answer = ask_llm("项目入口在哪里？")
        self.assertIn("--api-key", answer)

    def test_ask_llm_returns_message_when_model_missing(self) -> None:
        configure_llm(provider="aliyun", api_key="aliyun-key")
        answer = ask_llm("项目入口在哪里？")
        self.assertIn("--model", answer)

    def test_ask_llm_returns_message_when_model_not_registered(self) -> None:
        configure_llm(provider="aliyun", model="unknown-model", api_key="aliyun-key")
        answer = ask_llm("项目入口在哪里？")
        self.assertIn("模型未命中", answer)

    def test_ask_llm_calls_openai_compatible(self) -> None:
        fake_response = MagicMock()
        fake_response.output_text = "aliyun answer"
        fake_client = MagicMock()
        fake_client.responses.create.return_value = fake_response

        configure_llm(
            provider="aliyun",
            model="qwen-plus",
            api_key="aliyun-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        with patch("src.llm.client.OpenAI", return_value=fake_client) as mock_openai:
            answer = ask_llm("项目入口在哪里？")

        self.assertEqual(answer, "aliyun answer")
        mock_openai.assert_called_once_with(
            api_key="aliyun-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        fake_client.responses.create.assert_called_once_with(
            model="qwen-plus",
            input="项目入口在哪里？",
            temperature=0.2,
        )


if __name__ == "__main__":
    unittest.main()
