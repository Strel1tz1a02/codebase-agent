from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.llm.client import _runtime_config, ask_llm, configure_llm
from src.llm.providers import (
    PROVIDER_REGISTRY,
    get_default_base_url,
    get_provider_models,
    get_registered_providers,
)


class TestLLMClient(unittest.TestCase):
    def setUp(self) -> None:
        configure_llm()

    def test_ask_llm_returns_message_when_provider_missing(self) -> None:
        answer = ask_llm("Where is the project entry?")
        self.assertIn("--provider", answer)

    def test_registered_providers_contains_aliyun_and_deepseek(self) -> None:
        self.assertEqual(get_registered_providers(), {"aliyun", "deepseek"})

    def test_each_provider_has_base_url_config(self) -> None:
        for provider in get_registered_providers():
            with self.subTest(provider=provider):
                self.assertTrue(get_default_base_url(provider))

    def test_provider_model_registry_contains_core_models(self) -> None:
        self.assertIn("qwen-plus", get_provider_models("aliyun"))
        self.assertIn("deepseek-chat", get_provider_models("deepseek"))

    def test_ask_llm_returns_message_when_api_key_missing(self) -> None:
        configure_llm(provider="aliyun", model="qwen-plus")
        answer = ask_llm("Where is the project entry?")
        self.assertIn("--api-key", answer)

    def test_ask_llm_returns_message_when_model_missing(self) -> None:
        configure_llm(provider="aliyun", api_key="aliyun-key")
        answer = ask_llm("Where is the project entry?")
        self.assertIn("--model", answer)

    def test_ask_llm_returns_message_when_model_not_registered(self) -> None:
        configure_llm(provider="aliyun", model="unknown-model", api_key="aliyun-key")
        answer = ask_llm("Where is the project entry?")
        self.assertIn("模型未命中", answer)

    def test_ask_llm_calls_openai_compatible_chat_completion(self) -> None:
        fake_response = MagicMock()
        fake_response.choices = [MagicMock(message=MagicMock(content="aliyun answer"))]
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_response

        configure_llm(
            provider="aliyun",
            model="qwen-plus",
            api_key="aliyun-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        with patch("src.llm.client.OpenAI", return_value=fake_client) as mock_openai:
            answer = ask_llm("Where is the project entry?")

        self.assertEqual(answer, "aliyun answer")
        mock_openai.assert_called_once_with(
            api_key="aliyun-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        fake_client.chat.completions.create.assert_called_once_with(
            model="qwen-plus",
            messages=[{"role": "user", "content": "Where is the project entry?"}],
            temperature=0.2,
        )

    def test_ask_llm_uses_default_base_url_for_registered_providers(self) -> None:
        provider_model_pairs = {
            "aliyun": "qwen-plus",
            "deepseek": "deepseek-chat",
        }

        for provider, model in provider_model_pairs.items():
            with self.subTest(provider=provider):
                fake_response = MagicMock()
                fake_response.choices = [MagicMock(message=MagicMock(content="answer"))]
                fake_client = MagicMock()
                fake_client.chat.completions.create.return_value = fake_response

                configure_llm(provider=provider, model=model, api_key="test-key")
                with patch("src.llm.client.OpenAI", return_value=fake_client) as mock_openai:
                    answer = ask_llm("Where is the project entry?")

                self.assertEqual(answer, "answer")
                mock_openai.assert_called_once_with(
                    api_key="test-key",
                    base_url=get_default_base_url(provider),
                )
                fake_client.chat.completions.create.assert_called_once()

    def test_configure_llm_sets_default_base_url_in_runtime_config(self) -> None:
        configure_llm(provider="deepseek")
        self.assertEqual(_runtime_config["base_url"], get_default_base_url("deepseek"))

    def test_provider_registry_uses_provider_name_as_key(self) -> None:
        for provider, provider_info in PROVIDER_REGISTRY.items():
            with self.subTest(provider=provider):
                self.assertEqual(provider_info.name, provider)


if __name__ == "__main__":
    unittest.main()
