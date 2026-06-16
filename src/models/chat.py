from __future__ import annotations

import os

from langchain_openai import ChatOpenAI

from src.core.config import AppConfig
from src.core.errors import ConfigurationError
from src.models.providers import get_default_base_url


def build_chat_model(config: AppConfig) -> ChatOpenAI:
    """
    输入：
        config：AppConfig，包含 provider、model、api_key_env、base_url、temperature。
    输出：
        ChatOpenAI：LangChain 的 OpenAI-compatible chat model 对象。
    作用：
        根据项目配置创建可被 LangChain / LangGraph 使用的聊天模型。
    设计原因：
        Graph 节点不应该直接读取环境变量或关心 provider 细节，统一放在模型工厂里处理。
    """
    model_config = config.model_config
    api_key = os.getenv(model_config.api_key_env, "").strip()
    if not api_key:
        raise ConfigurationError(f"missing api key env: {model_config.api_key_env}")
    base_url = model_config.base_url or get_default_base_url(model_config.provider)
    return ChatOpenAI(
        model=model_config.model,
        api_key=api_key,
        base_url=base_url or None,
        temperature=model_config.temperature,
    )
