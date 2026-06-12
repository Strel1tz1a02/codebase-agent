from __future__ import annotations

from src.llm.client import ask_llm
from src.prompts.templates import build_project_qa_prompt
from src.tools.scanning import read_context_files, select_context_files


def answer_project_question(scan_result: dict[str, object], question: str) -> dict[str, object]:
    """
    输入：
        scan_result：V1 已经扫描好的项目结构结果。
        question：用户针对项目提出的问题。
    输出：
        dict[str, object]：包含回答文本、使用到的上下文文件和最终 prompt。
    作用：
        基于已有扫描结果完成一次项目问答。
    设计原因：
        将 V1.5 关键步骤串联在一个入口中，便于 CLI 和后续 Agent 流程复用。
    """
    repo_path = str(scan_result.get("repo_path", ""))
    selected_files = select_context_files(scan_result, repo_path)
    file_contents = read_context_files(selected_files)
    prompt = build_project_qa_prompt(
        repo_summary=scan_result,
        question=question,
        file_contents=file_contents,
    )
    answer = ask_llm(prompt)
    return {
        "answer": answer,
        "used_files": selected_files,
        "prompt": prompt,
    }
