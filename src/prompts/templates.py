from __future__ import annotations


def build_project_qa_prompt(
    repo_summary: dict[str, object],
    question: str,
    file_contents: dict[str, str] | None = None,
) -> str:
    """
    输入：
        repo_summary：V1 扫描结果，包含目录树、文件类型统计、主要目录、入口文件候选等信息。
        question：用户针对项目提出的问题。
        file_contents：关键上下文文件内容映射（路径 -> 内容），可选。
    输出：
        str：可以发送给 LLM 的完整 prompt。
    作用：
        将 V1 的结构化扫描结果、关键文件内容和用户问题拼接成项目问答提示词。
    设计原因：
        V1.5 暂时不做 RAG，先让 LLM 基于项目结构和少量关键文件信息回答问题，
        因此需要一个稳定的 prompt 构造入口。
    """
    tree = repo_summary.get("tree", "")
    file_types = repo_summary.get("file_types", {})
    key_dirs = repo_summary.get("key_dirs", [])
    entry_candidates = repo_summary.get("entry_candidates", [])
    context_files = file_contents or {}

    file_content_blocks: list[str] = []
    for file_path, content in context_files.items():
        file_content_blocks.append(f"### {file_path}\n```text\n{content}\n```")
    file_contents_text = "\n\n".join(file_content_blocks) if file_content_blocks else "[未提供关键文件内容]"

    return f"""你是一个代码仓库分析助手。

请只基于我提供的项目结构和关键文件内容回答问题。
如果当前信息不足，请明确说明“不确定”，并告诉我下一步应该读取哪些文件。
回答中尽量引用相关文件路径。

请按以下 Markdown 格式回答：

## 回答
直接回答用户问题。

## 依据
列出你使用到的项目信息或文件路径。

## 不确定信息
如果当前上下文不足，说明哪里不确定。

## 下一步建议
如果需要更多信息，说明下一步应该读取哪些文件。

项目目录树：
{tree}

文件类型统计：
{file_types}

主要目录：
{key_dirs}

入口文件候选：
{entry_candidates}

关键文件内容：
{file_contents_text}

用户问题：
{question}
"""
