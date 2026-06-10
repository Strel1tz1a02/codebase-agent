import pytest

from src.core.config import ModelConfig
from src.core.errors import ConfigurationError
from src.models.chat import build_chat_model


def test_build_chat_model_requires_api_key_env(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    config = ModelConfig(api_key_env="MISSING_KEY")

    with pytest.raises(ConfigurationError):
        build_chat_model(config)


def test_build_chat_model_uses_openai_compatible_base_url(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "secret")
    config = ModelConfig(
        provider="deepseek",
        model="deepseek-chat",
        api_key_env="TEST_KEY",
        base_url="https://api.deepseek.com/v1",
    )

    model = build_chat_model(config)

    assert model.model_name == "deepseek-chat"
