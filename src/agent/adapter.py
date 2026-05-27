from __future__ import annotations

import json
import re

from src.llm.client import ask_llm


def build_prompt(context: dict[str, object]) -> str:
    """
    输入：
        context：AgentContext.to_dict() 生成的上下文字典。
    输出：
        str：给 LLM 的提示词文本。
    作用：
        明确告诉 LLM 只允许返回指定 JSON 结构。
    设计原因：
        先把输出协议约束清楚，能显著减少后续 parse 失败率。
    """
    context_json = json.dumps(context, ensure_ascii=False, indent=2)# ensure_ascii=False: 允许输出非 ASCII 字符（如中文），indent=2: 美化输出 JSON，使其更易读。
    return (
        "你是代码仓库分析 Agent 的决策器。\n"
        "请基于给定 context 做下一步决策。\n"
        "只允许返回 JSON，不要输出任何解释文字。\n"
        "只允许以下两种格式之一：\n"
        '{"decision":"tool","tool_name":"tool_stub_a","arguments":{}}\n'
        '{"decision":"answer","answer":"..."}\n\n'
        "context:\n"
        f"{context_json}\n"
    )


def _extract_json_text(text: str) -> str:# _extract_json_text: 从 LLM 返回的文本中提取 JSON 字符串，支持纯 JSON 或 fenced code block 两种格式。
    fenced = re.search(r"```json\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced is not None:
        return fenced.group(1).strip()
    return text.strip()


def parse_llm(text: str) -> dict[str, object]:
    """
    输入：
        text：LLM 返回的原始文本。
    输出：
        dict：解析出的 decision 字典；失败时返回 decision=invalid。
    作用：
        将 LLM 文本安全转换为控制器可消费的数据结构。
    设计原因：
        真实 LLM 输出可能是纯 JSON 或 fenced code block，需要统一兜底处理。
    """
    try:
        json_text = _extract_json_text(text)
        payload = json.loads(json_text)
        if isinstance(payload, dict):
            return payload # 检验问题放在 controller 里，保持这一层的单一职责。
        return {"decision": "invalid", "error": "parsed JSON is not an object"}
    except Exception as exc:
        return {"decision": "invalid", "error": f"json parse failed: {exc}"}


def next_decision(context: dict[str, object]) -> dict[str, object]:
    """
    输入：
        context：AgentContext.to_dict() 生成的上下文字典。
    输出：
        dict：decision payload。
    作用：
        将“prompt 构造 -> LLM 调用 -> JSON 解析”串成一步。
    设计原因：
        给 controller 一个单入口，后续切换模型实现时只改这一层。
    """
    prompt = build_prompt(context)
    text = ask_llm(prompt)
    return parse_llm(text)
