from __future__ import annotations

from src.runtime.sessions import RuntimeSession


def build_memory_messages(session: RuntimeSession, current_question: str) -> list[dict[str, str]]:
    """
    输入：
        session：当前 run 所属 session。
        current_question：当前用户问题。
    输出：
        list[dict[str, str]]：按时间顺序排列的 user/assistant 对话消息。
    作用：
        将同一 session 的历史 run 转成 graph 可消费的 messages，并追加当前问题。
    为什么需要这个函数：
        多轮上下文后续会扩展窗口裁剪、摘要和过滤策略，集中放在 memory 模块更容易演进。
    """
    messages: list[dict[str, str]] = []
    for previous_run in session.runs.values():
        if previous_run.question:
            messages.append({"role": "user", "content": previous_run.question})
        if previous_run.answer:
            messages.append({"role": "assistant", "content": previous_run.answer})
    messages.append({"role": "user", "content": current_question})
    return messages
