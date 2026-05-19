from __future__ import annotations

from src.llm.client import ask_llm
from src.prompts.templates import build_project_qa_prompt


def answer_project_question(scan_result: dict[str, object], question: str) -> str:
    """
    输入：
        scan_result：V1 已经扫描好的项目结构结果。
        question：用户针对项目提出的问题。
    输出：
        str：LLM 返回的回答文本。当前阶段来自占位版 ask_llm。
    作用：
        基于已有扫描结果完成一次项目问答。
    设计原因：
        扫描逻辑由 main.py 负责；问答模块只消费 scan_result，避免隐藏的重复扫描。
    """
    prompt = build_project_qa_prompt(scan_result, question)
    return ask_llm(prompt)
