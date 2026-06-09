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
        '{"decision":"tool","tool_name":"repo_summary","arguments":{}}\n'
        '{"decision":"tool","tool_name":"read_file","arguments":{"path":"src/main.py"}}\n'
        '{"decision":"tool","tool_name":"search_code","arguments":{"keyword":"run_agent_loop","scope":"src"}}\n'
        '{"decision":"tool","tool_name":"retrieve_code","arguments":{"query":"agent loop tool execution","top_k":5}}\n'
        '{"decision":"answer","answer":"..."}\n\n'
        "context.messages 是当前 session 的多轮对话历史，按时间顺序排列。\n"
        "如果当前问题是追问，例如“那它呢”“继续解释”“它怎么运行”，请结合 messages 理解用户指代。\n"
        "messages 只用于理解对话上下文；工具调用仍然必须基于当前 question 选择合适工具。\n\n"
        "repo_summary 用于查看仓库的文件数、主要目录和入口候选。\n"
        "如果问题要求先查看仓库概况，优先调用 repo_summary。\n\n"
        "read_file 用于读取仓库内指定文件内容，arguments.path 必须是仓库内相对路径。\n"
        "如果问题要求读取、查看或解释某个具体文件，优先调用 read_file。\n\n"
        "search_code 用于按关键词搜索代码文件并返回相对路径、行号和当前行文本。\n"
        "search_code.arguments.scope 可选 src/tests/docs/all；默认用 src。\n"
        "如果问题包含明确函数名、类名或关键词，优先调用 search_code；除非用户明确要求测试、文档或全仓库，否则 scope 使用 src。\n\n"
        "retrieve_code 用于基于 RAG 索引做语义检索，返回 relative_path、start_line、end_line、content 和 score。\n"
        "如果问题是概念性、流程性、跨文件理解，或没有明确关键词，优先调用 retrieve_code。\n"
        "retrieve_code.arguments.query 应该是用户问题的精简检索语句，top_k 默认 5。\n"
        "如果最终答案使用了 retrieve_code 的结果，必须包含引用，格式为 [relative_path:start_line-end_line]。\n\n"
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
