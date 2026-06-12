from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 将项目根目录加入模块搜索路径，确保可通过 python src/main.py 直接运行 src.* 导入。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm.client import configure_llm
from src.llm.providers import format_provider_help
from src.agent.adapter import next_decision
from src.agent.controller import run_agent_loop
from src.agent.graph import run_agent_graph
from src.config import DEFAULT_CONFIG_PATH, get_llm_config, load_app_config, merge_cli_args
from src.qa import answer_project_question
from src.rag import chunk_code_files, load_code_files
from src.rag.retrieval import retrieve_relevant_chunks
from src.tools.legacy_file_tools import generate_v1_report, run_v1_scan


def _format_history_arguments(arguments: dict[str, object]) -> str:
    """
    输入:
        arguments: 工具调用参数字典。
    输出:
        str: 适合终端阅读的一行参数文本。
    作用:
        把 {"keyword": "...", "scope": "..."} 这类参数转成 key=value 形式。
    为什么需要这个函数:
        终端直接打印 dict 噪声较大，格式化后更容易看清 Agent 为什么调用某个工具。
    """
    if not arguments:
        return "{}"
    return ", ".join(f"{key}={value}" for key, value in arguments.items())


def _format_history_match(match: dict[str, object]) -> str:
    """
    输入:
        match: search_code 或 retrieve_code 返回的一条命中记录。
    输出:
        str: 适合终端展示的一行命中文本。
    作用:
        同时支持关键词搜索的 path/line/text 和 RAG 检索的 relative_path/行号区间/content。
    为什么需要这个函数:
        V5 新增 retrieve_code 后，History 需要展示可引用的路径和行号范围。
    """
    if "relative_path" in match:
        content_preview = str(match.get("content", "")).strip().replace("\n", "\\n")[:120]
        return (
            f"{match.get('relative_path', '')}:"
            f"{match.get('start_line', '')}-{match.get('end_line', '')} "
            f"score={float(match.get('score', 0.0)):.6f} "
            f"{content_preview}"
        )

    return (
        f"{match.get('path', '')}:"
        f"{match.get('line', '')} "
        f"{match.get('text', '')}"
    )


def _print_history(history: object) -> None:
    """
    输入:
        history: Agent 返回结果中的 history 字段。
    输出:
        无，直接打印到终端。
    作用:
        将 Agent 的 decision/tool_result 历史格式化成分步骤的终端输出。
    为什么需要这个函数:
        原始 history 是嵌套字典，直接打印不利于调试。分步骤输出可以清楚看到
        LLM 选择了什么工具、传了什么参数、工具返回了什么摘要。
    """
    print("## History")
    if not isinstance(history, list) or not history:
        print("- 无")
        return

    step_number = 0
    for item in history:
        if not isinstance(item, dict):
            print(f"- {item}")
            continue

        item_type = str(item.get("type", ""))
        data = item.get("data", {})
        if not isinstance(data, dict):
            print(f"- {item}")
            continue

        if item_type == "decision":
            step_number += 1
            tool_name = str(data.get("tool_name", ""))
            arguments = data.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}

            print(f"### Step {step_number}: Decision")
            print(f"- Decision: {data.get('decision', '')}")
            if tool_name:
                print(f"- Tool: {tool_name}")
            print(f"- Arguments: {_format_history_arguments(arguments)}")
            continue

        if item_type == "tool_result":
            if step_number == 0:
                step_number = 1

            print(f"### Step {step_number}: Tool Result")
            print(f"- Tool: {data.get('tool_name', '')}")
            print(f"- OK: {data.get('ok', False)}")
            error = str(data.get("error", ""))
            if error:
                print(f"- Error: {error}")

            output = data.get("output", {})
            if isinstance(output, dict):
                matches = output.get("matches", [])
                if isinstance(matches, list):
                    print(f"- Matches: {len(matches)}")
                    for index, match in enumerate(matches[:5], start=1):
                        if not isinstance(match, dict):
                            continue
                        print(f"  {index}. {_format_history_match(match)}")
            continue

        print(f"- {item}")


def parse_args() -> argparse.Namespace:
    """
    输入：
        无（从命令行读取参数）。
    输出：
        argparse.Namespace，包含解析后的参数。
    作用：
        统一管理 V1/V1.5 命令行参数定义。
    设计原因：
        参数解析与业务逻辑解耦，便于后续扩展更多开关。
    """
    parser = argparse.ArgumentParser(description="V1 项目结构扫描器")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="应用配置文件路径")
    parser.add_argument("--repo", help="待分析的本地项目路径（可覆盖配置文件）")
    parser.add_argument("--ask", help="针对项目提问，触发问答流程")
    parser.add_argument("--provider", help=f"LLM provider: {format_provider_help()}")
    parser.add_argument("--model", help="LLM model name")
    parser.add_argument("--api-key", dest="api_key", help="LLM API key")
    parser.add_argument("--base-url", dest="base_url", help="LLM API base URL")
    parser.add_argument("--build-chunks", action="store_true", help="V2: build code chunks only")
    parser.add_argument(
        "--ask-mode",
        choices=["basic", "rag", "agent", "graph"],
        default=None,
        help="ask mode: basic or rag or agent or graph",
    )
    parser.add_argument("--top-k", type=int, default=None, help="top K chunks for rag mode")
    parser.add_argument("--reindex", action="store_true", help="force rebuild rag cache index")
    parser.add_argument("--max-steps", type=int, help="max steps for agent loop")
    return parser.parse_args()


def main() -> None:
    """
    输入：
        无（使用 parse_args 获取参数）。
    输出：
        无（将结果打印到标准输出）。
    作用：
        执行 V1 扫描或 V1.5 问答流程。
    设计原因：
        作为程序入口，保持流程清晰：解析参数 -> 扫描 -> 渲染/问答 -> 输出。
    """
    args = parse_args()
    config_path = str(getattr(args, "config", DEFAULT_CONFIG_PATH))
    app_config: dict[str, object]
    try:
        app_config = load_app_config(config_path)
    except FileNotFoundError:
        print(
            f"配置文件不存在：{config_path}\n"
            "请先复制 .codebase_agent/config.example.json 为 .codebase_agent/config.json 并按需修改。"
        )
        app_config = {}

    merged_config = merge_cli_args(app_config, args)
    repo_path = str(merged_config.get("repo", "")).strip()
    ask_mode = str(merged_config.get("ask_mode", "basic")).strip() or "basic"

    rag_cfg = merged_config.get("rag", {})
    if not isinstance(rag_cfg, dict):
        rag_cfg = {}
    top_k = int(rag_cfg.get("top_k", 5))
    reindex = bool(rag_cfg.get("reindex", False))

    agent_cfg = merged_config.get("agent", {})
    if not isinstance(agent_cfg, dict):
        agent_cfg = {}
    max_steps = int(agent_cfg.get("max_steps", 3))

    if getattr(args, "build_chunks", False):
        if not repo_path:
            print("缺少 repo 配置：请在 config.json 中设置 repo 或通过 --repo 传入。")
            return
        file_records = load_code_files(repo_path)
        chunks = chunk_code_files(file_records)
        print(f"Total files: {len(file_records)}")
        print(f"Total chunks: {len(chunks)}")
        print()
        print("Top 5 chunks:")
        for chunk in chunks[:5]:
            content_preview = str(chunk.get("content", "")).replace("\n", "\\n")[:120]
            print(f"- id: {chunk.get('id', '')}")
            print(f"  relative_path: {chunk.get('relative_path', '')}")
            print(f"  start_line: {chunk.get('start_line', 0)}")
            print(f"  end_line: {chunk.get('end_line', 0)}")
            print(f"  preview: {content_preview}")
        return

    if args.ask:
        if not repo_path:
            print("缺少 repo 配置：请在 config.json 中设置 repo 或通过 --repo 传入。")
            return

        if ask_mode in {"agent", "graph"}:
            llm_cfg = get_llm_config(merged_config)
            configure_llm(
                provider=llm_cfg.get("provider"),
                model=llm_cfg.get("model"),
                api_key=llm_cfg.get("api_key"),
                base_url=llm_cfg.get("base_url"),
            )
            if ask_mode == "graph":
                agent_result = run_agent_graph(
                    question=args.ask,
                    repo_path=repo_path,
                    llm_decision_func=next_decision,
                    max_steps=max_steps,
                )
            else:
                agent_result = run_agent_loop(
                    question=args.ask,
                    repo_path=repo_path,
                    llm_decision_func=next_decision,
                    max_steps=max_steps,
                )
            print("## Agent Status")
            print(str(agent_result.get("status", "")))
            print()
            print("## 回答")
            print(str(agent_result.get("answer", "")))
            if "reason" in agent_result:
                print()
                print("## 停止原因")
                print(str(agent_result.get("reason", "")))
            print()
            _print_history(agent_result.get("history", []))
            return

        if ask_mode == "rag":
            hits = retrieve_relevant_chunks(
                args.ask,
                repo_path,
                top_k=top_k,
                reindex=reindex,
            )
            print("## Top-K Hits")
            if hits:
                for hit in hits:
                    print(
                        f"- score={float(hit.get('score', 0.0)):.6f} "
                        f"id={hit.get('id', '')} "
                        f"path={hit.get('relative_path', '')} "
                        f"lines={hit.get('start_line', 0)}-{hit.get('end_line', 0)}"
                    )
            else:
                print("- [NO_HIT]")
            return

        scan_result = run_v1_scan(repo_path)
        llm_cfg = get_llm_config(merged_config)
        configure_llm(
            provider=llm_cfg.get("provider"),
            model=llm_cfg.get("model"),
            api_key=llm_cfg.get("api_key"),
            base_url=llm_cfg.get("base_url"),
        )
        qa_result = answer_project_question(scan_result, args.ask)
        answer_text = str(qa_result.get("answer", ""))
        used_files = qa_result.get("used_files", [])
        prompt_text = str(qa_result.get("prompt", ""))

        print("## Prompt")
        print(prompt_text)
        print()

        print("## 回答")
        print(answer_text)
        print()

        print("## 使用的上下文文件")
        if isinstance(used_files, list) and used_files:
            for file_path in used_files:
                print(f"- {file_path}")
        else:
            print("- 无")
        return

    if not repo_path:
        print("缺少 repo 配置：请在 config.json 中设置 repo 或通过 --repo 传入。")
        return
    scan_result = run_v1_scan(repo_path)
    report = generate_v1_report(scan_result)
    print(report)


if __name__ == "__main__":
    main()
