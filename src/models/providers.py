from __future__ import annotations


DEFAULT_BASE_URLS = {
    "aliyun": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


def get_default_base_url(provider: str) -> str:
    """
    输入：
        provider：模型服务商名称，例如 aliyun、deepseek。
    输出：
        str：该服务商的默认 OpenAI-compatible base_url；未知服务商返回空字符串。
    作用：
        根据 provider 查找默认接口地址。
    设计原因：
        后续创建模型客户端时，只需要传入 provider，就能自动补全常用 base_url。
    """
    normalized_provider = provider.strip().lower()
    return DEFAULT_BASE_URLS.get(normalized_provider, "")
