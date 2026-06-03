from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    default_base_url: str
    recommended_models: tuple[str, ...]


PROVIDER_REGISTRY: dict[str, ProviderInfo] = {
    "aliyun": ProviderInfo(
        name="aliyun",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        recommended_models=("qwen-turbo", "qwen-plus", "qwen-max"),
    ),
    "deepseek": ProviderInfo(
        name="deepseek",
        default_base_url="https://api.deepseek.com/v1",
        recommended_models=("deepseek-chat", "deepseek-reasoner"),
    ),
}


def get_registered_providers() -> set[str]:
    return set(PROVIDER_REGISTRY.keys())


def get_provider_models(provider: str) -> set[str]:
    provider_info = PROVIDER_REGISTRY.get(provider)
    if provider_info is None:
        return set()
    return set(provider_info.recommended_models)


def get_default_base_url(provider: str) -> str:
    provider_info = PROVIDER_REGISTRY.get(provider)
    if provider_info is None:
        return ""
    return provider_info.default_base_url


def format_provider_help() -> str:
    return ", ".join(sorted(PROVIDER_REGISTRY.keys()))
