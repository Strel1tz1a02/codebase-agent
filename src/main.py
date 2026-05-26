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
from src.qa import answer_project_question
from src.rag import chunk_code_files, load_code_files
from src.rag.retrieval import retrieve_relevant_chunks
from src.tools.file_tools import generate_v1_report, run_v1_scan


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
    parser.add_argument("--repo", required=True, help="待分析的本地项目路径")
    parser.add_argument("--ask", help="针对项目提问，触发问答流程")
    parser.add_argument("--provider", help=f"LLM provider: {format_provider_help()}")
    parser.add_argument("--model", help="LLM model name")
    parser.add_argument("--api-key", dest="api_key", help="LLM API key")
    parser.add_argument("--base-url", dest="base_url", help="LLM API base URL")
    parser.add_argument("--build-chunks", action="store_true", help="V2: build code chunks only")
    parser.add_argument("--ask-mode", choices=["basic", "rag"], default="basic", help="ask mode: basic or rag")
    parser.add_argument("--top-k", type=int, default=5, help="top K chunks for rag mode")
    parser.add_argument("--reindex", action="store_true", help="force rebuild rag cache index")
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

    if getattr(args, "build_chunks", False):
        file_records = load_code_files(args.repo)
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

    scan_result = run_v1_scan(args.repo)

    if args.ask:
        ask_mode = getattr(args, "ask_mode", "basic")
        if ask_mode == "rag":
            hits = retrieve_relevant_chunks(
                args.ask,
                args.repo,
                top_k=getattr(args, "top_k", 5),
                reindex=getattr(args, "reindex", False),
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

        configure_llm(
            provider=args.provider,
            model=args.model,
            api_key=args.api_key,
            base_url=args.base_url,
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

    report = generate_v1_report(scan_result)
    print(report)


if __name__ == "__main__":
    main()
