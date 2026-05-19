from __future__ import annotations


def ask_llm(prompt: str) -> str:
    """
    输入：
        prompt：要发送给 LLM 的完整提示词。
    输出：
        str：LLM 的回答文本。当前阶段先返回占位内容。
    作用：
        为 V1.5 提供一个最小的 LLM 调用入口。
    设计原因：
        先把“项目问答流程需要调用 LLM”这个接口固定下来，后续再逐步替换为真实 API 调用。
    """
    return f"TODO: call LLM with prompt: {prompt}"

