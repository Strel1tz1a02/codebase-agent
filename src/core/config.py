from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelConfig:
    """
    输入：
        provider：模型服务商名称，例如 aliyun、deepseek。
        model：具体模型名称，例如 qwen-plus。
        api_key_env：保存 API Key 的环境变量名。
        base_url：OpenAI-compatible 接口地址，可为空。
        temperature：模型回答随机性，数值越低越稳定。
    输出：
        ModelConfig：规范化后的模型配置对象。
    作用：
        集中保存 LLM 模型相关配置。
    设计原因：
        让后续模型工厂、Graph 节点不直接关心 CLI 参数或环境变量细节。
    """

    provider: str = "aliyun"
    model: str = "qwen-plus"
    api_key_env: str = "CODEBASE_AGENT_API_KEY"
    base_url: str = ""
    temperature: float = 0.2

    def __post_init__(self) -> None:
        """
        输入：
            self：刚创建好的 ModelConfig 对象。
        输出：
            None，直接更新 self.provider。
        作用：
            把 provider 去掉首尾空格并转换成小写。
        设计原因：
            用户可能输入 Aliyun、 aliyun 等形式，统一后方便后续查 provider 注册表。
        """
        self.provider = self.provider.strip().lower()
