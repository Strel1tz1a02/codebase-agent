from __future__ import annotations

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 运行时配置，允许通过 configure_llm() 注入参数，ask_llm() 读取使用。
_runtime_config: dict[str, str] = {
    "provider": "",
    "model": "",
    "api_key": "",
    "base_url": "",
}

# 已注册的提供商与主流可用模型（含国内常见免费档/免费模型）。
PROVIDER_MODEL_REGISTRY: dict[str, set[str]] = {
    "openai": {"gpt-4o-mini"},
    "aliyun": {"qwen-turbo", "qwen-plus", "qwen-max"},
    "deepseek": {"deepseek-chat", "deepseek-reasoner"},
    "siliconflow": {
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-R1",
        "Qwen/Qwen2.5-7B-Instruct",
    },
    "zhipu": {"glm-4-flash", "glm-4-plus", "glm-4v-flash"},
    "baidu": {"ernie-speed-128k", "ernie-4.0-turbo-8k", "deepseek-v3"},
}
REGISTERED_PROVIDERS: set[str] = set(PROVIDER_MODEL_REGISTRY.keys())


def configure_llm(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> None:
    """
    输入：
        provider：LLM 提供商名称。
        model：模型名称。
        api_key：API Key。
        base_url：API 基础地址。
    输出：
        无，更新模块内运行时配置。
    作用：
        允许上层从命令行参数注入 LLM 配置。
    设计原因：
        保持 ask_llm(prompt) 接口不变，同时实现“只从运行时配置读取”。
    """
    _runtime_config.update(
        {
            "provider": "",
            "model": "",
            "api_key": "",
            "base_url": "",
        }
    )
    if provider is not None:
        _runtime_config["provider"] = provider.strip()
    if model is not None:
        _runtime_config["model"] = model.strip()
    if api_key is not None:
        _runtime_config["api_key"] = api_key.strip()
    if base_url is not None:
        _runtime_config["base_url"] = base_url.strip()


def ask_llm(prompt: str) -> str:
    """
    输入：
        prompt：要发送给 LLM 的完整提示词。
    输出：
        str：LLM 的回答文本，或可读错误提示。
    作用：
        为 V1.5 提供真实的 LLM 调用入口，并支持切换 API 提供商。
    设计原因：
        保持上层接口不变，把配置读取、模型调用和异常兜底收敛在一个函数里，
        避免上层流程因网络或配置问题崩溃。
    """
    provider = _runtime_config.get("provider").strip().lower()
    if provider not in REGISTERED_PROVIDERS:
        return "LLM 提供商配置错误：请通过 --provider 提供已注册的提供商名称。"

    model = _runtime_config.get("model").strip()
    api_key = _runtime_config.get("api_key").strip()
    base_url = _runtime_config.get("base_url").strip()

    if not api_key:
        return "LLM API Key 缺失：请通过 --api-key 提供。"
    if not model:
        return "LLM 模型未配置：请通过 --model 提供。"

    provider_models = PROVIDER_MODEL_REGISTRY.get(provider, set())
    if model not in provider_models:
        return "LLM 模型未命中：当前 provider 未注册该模型，请检查 --model 是否正确。"

    if OpenAI is None:
        return "LLM SDK 缺失：请先安装 openai 依赖。"

    try:
        client_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = OpenAI(**client_kwargs)
        response = client.responses.create(
            model=model,
            input=prompt,
            temperature=0.2,
        )

        output_text = getattr(response, "output_text", "")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
        return "LLM 返回为空：模型未提供有效文本内容。"
    except Exception as exc:
        return f"LLM 调用失败：{exc}"
