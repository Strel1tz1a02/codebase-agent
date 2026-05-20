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
    "aliyun": {"qwen-turbo", "qwen-plus", "qwen-max"},
    "deepseek": {"deepseek-chat", "deepseek-reasoner"},
}
REGISTERED_PROVIDERS: set[str] = set(PROVIDER_MODEL_REGISTRY.keys())
PROVIDER_DEFAULT_BASE_URLS: dict[str, str] = {
    "aliyun": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


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
    elif _runtime_config["provider"]:
        _runtime_config["base_url"] = PROVIDER_DEFAULT_BASE_URLS.get(_runtime_config["provider"], "")


def _load_and_validate_config() -> tuple[dict[str, str] | None, str | None]:
    """
    输入：
        无，从运行时配置读取参数。
    输出：
        (config, error_message)
        - config：校验通过时返回包含 provider/model/api_key/base_url 的字典
        - error_message：校验失败时返回可读错误文本
    作用：
        统一处理参数获取与合法性校验。
    设计原因：
        将 ask_llm 的配置处理逻辑独立出来，便于维护和测试。
    """
    provider = _runtime_config.get("provider", "").strip().lower()
    model = _runtime_config.get("model", "").strip()
    api_key = _runtime_config.get("api_key", "").strip()
    base_url = _runtime_config.get("base_url", "").strip()

    if provider not in REGISTERED_PROVIDERS:
        return None, "LLM 提供商配置错误：请通过 --provider 提供已注册的提供商名称。"
    if not api_key:
        return None, "LLM API Key 缺失：请通过 --api-key 提供。"
    if not model:
        return None, "LLM 模型未配置：请通过 --model 提供。"
    provider_models = PROVIDER_MODEL_REGISTRY.get(provider, set())
    if model not in provider_models:
        return None, "LLM 模型未命中：当前 provider 未注册该模型，请检查 --model 是否正确。"

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    }, None


def _call_remote_model(prompt: str, config: dict[str, str]):
    """
    输入：
        prompt：待发送给模型的提示词。
        config：已校验的调用配置。
    输出：
        模型 SDK 原始响应对象。
    作用：
        统一处理远端模型调用。
    设计原因：
        将网络调用与参数校验、响应解析解耦，降低函数复杂度。
    """
    if OpenAI is None:
        raise RuntimeError("LLM SDK 缺失：请先安装 openai 依赖。")

    client_kwargs: dict[str, str] = {"api_key": config["api_key"]}
    if config["base_url"]:
        client_kwargs["base_url"] = config["base_url"]

    client = OpenAI(**client_kwargs)
    return client.chat.completions.create(
        model=config["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )


def _parse_model_response(response) -> str:
    """
    输入：
        response：模型 SDK 返回的原始响应对象。
    输出：
        str：解析后的回答文本；为空时返回统一提示文本。
    作用：
        统一处理响应结构解析。
    设计原因：
        把响应解析逻辑独立出来，便于后续支持不同接口格式。
    """
    choices = getattr(response, "choices", [])
    if choices:
        message = getattr(choices[0], "message", None)
        output_text = getattr(message, "content", "")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()
    return "LLM 返回为空：模型未提供有效文本内容。"


def ask_llm(prompt: str) -> str:
    """
    输入：
        prompt：要发送给 LLM 的完整提示词。
    输出：
        str：LLM 的回答文本，或可读错误提示。
    作用：
        为 V1.5 提供真实的 LLM 调用入口，并支持切换 API 提供商。
    设计原因：
        保持上层接口不变，采用“配置读取 -> 远端调用 -> 响应解析”三段式流程。
    """
    config, error_message = _load_and_validate_config()
    if error_message is not None:
        return error_message

    try:
        response = _call_remote_model(prompt, config)
        return _parse_model_response(response)
    except Exception as exc:
        return f"LLM 调用失败：{exc}"
