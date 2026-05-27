from __future__ import annotations

import json
import os
from argparse import Namespace
from copy import deepcopy

DEFAULT_CONFIG_PATH = ".codebase_agent/config.json"


def load_app_config(path: str = DEFAULT_CONFIG_PATH) -> dict[str, object]:
    """
    输入：
        path：配置文件路径，默认 .codebase_agent/config.json。
    输出：
        dict：配置字典。
    作用：
        从本地 JSON 文件加载应用配置。
    设计原因：
        将固定配置从 CLI 参数中抽离，减少日常启动参数长度。
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("config file must contain a JSON object")
    return data


def merge_cli_args(config: dict[str, object], args: Namespace) -> dict[str, object]:
    """
    输入：
        config：文件配置。
        args：命令行参数。
    输出：
        dict：合并后的配置。
    作用：
        用 CLI 参数覆盖配置文件默认值。
    设计原因：
        允许“配置文件做默认，CLI 做临时覆盖”。
    """
    merged = deepcopy(config)

    llm_cfg = merged.setdefault("llm", {})
    rag_cfg = merged.setdefault("rag", {})
    agent_cfg = merged.setdefault("agent", {})

    repo = getattr(args, "repo", None)
    if repo:
        merged["repo"] = repo

    ask_mode = getattr(args, "ask_mode", None)
    if ask_mode:
        merged["ask_mode"] = ask_mode

    provider = getattr(args, "provider", None)
    if provider:
        llm_cfg["provider"] = provider

    model = getattr(args, "model", None)
    if model:
        llm_cfg["model"] = model

    base_url = getattr(args, "base_url", None)
    if base_url:
        llm_cfg["base_url"] = base_url

    api_key = getattr(args, "api_key", None)
    if api_key:
        llm_cfg["api_key"] = api_key

    top_k = getattr(args, "top_k", None)
    if top_k is not None:
        rag_cfg["top_k"] = top_k

    if bool(getattr(args, "reindex", False)):
        rag_cfg["reindex"] = True

    max_steps = getattr(args, "max_steps", None)
    if max_steps is not None:
        agent_cfg["max_steps"] = max_steps

    return merged


def get_llm_config(config: dict[str, object]) -> dict[str, str]:
    """
    输入：
        config：合并后的配置。
    输出：
        dict：provider/model/api_key/base_url。
    作用：
        解析 LLM 配置，并通过 api_key_env 读取真实 API Key。
    设计原因：
        API Key 不落盘，避免提交到 Git 仓库。
    """
    llm_cfg = config.get("llm", {})
    if not isinstance(llm_cfg, dict):
        llm_cfg = {}

    provider = str(llm_cfg.get("provider", ""))
    model = str(llm_cfg.get("model", ""))
    base_url = str(llm_cfg.get("base_url", ""))

    # CLI 直接覆盖的 api_key 优先；否则走环境变量读取。
    direct_api_key = str(llm_cfg.get("api_key", "")).strip()
    if direct_api_key:
        api_key = direct_api_key
    else:
        api_key_env = str(llm_cfg.get("api_key_env", "")).strip()
        api_key = os.getenv(api_key_env, "") if api_key_env else ""

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    }
