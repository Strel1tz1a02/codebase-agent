from __future__ import annotations

from src.runtime.session import RuntimeSession


def summarize_latest_run(session: RuntimeSession, chat_model: object) -> str:
    latest_run = _latest_run(session)
    if latest_run is None or not callable(getattr(chat_model, "invoke", None)):
        return ""

    prompt = _build_run_summary_prompt(
        question=str(getattr(latest_run, "question", "")),
        answer=str(getattr(latest_run, "answer", "")),
    )
    response = chat_model.invoke(prompt)
    summary = str(getattr(response, "content", response)).strip()
    if not summary:
        return ""
    return f"[run_id={getattr(latest_run, 'run_id', '')}]\n{summary}"


def update_memory_summary(session: RuntimeSession, chat_model: object) -> str:
    new_summary = summarize_latest_run(session, chat_model)
    return append_memory_summary(session.memory_summary, new_summary)


def append_memory_summary(previous_summary: str, new_summary: str) -> str:
    previous = previous_summary.strip()
    new = new_summary.strip()
    if not new:
        return previous
    if not previous:
        return new
    return f"{previous}\n\n{new}"


def _latest_run(session: RuntimeSession) -> object | None:
    if not session.runs:
        return None
    return next(reversed(session.runs.values()))# next() 从迭代器中取出下一个元素


def _build_run_summary_prompt(question: str, answer: str) -> str:
    return (
        "请把下面这一轮对话压缩成可长期保留的会话记忆。\n"
        "只保留对后续回答有用的信息，例如用户身份、偏好、项目目标、已确认设计、未完成事项。\n"
        "不要复述无用寒暄；如果没有值得保留的信息，输出空字符串。\n\n"
        f"用户：{question}\n"
        f"助手：{answer}\n"
    )
