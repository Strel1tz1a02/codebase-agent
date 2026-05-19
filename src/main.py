from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 将项目根目录加入模块搜索路径，确保可通过 python src/main.py 直接运行 src.* 导入。
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.qa import answer_project_question
from src.tools.file_tools import generate_v1_report, run_v1_scan


def parse_args() -> argparse.Namespace:
    """
    输入：
        无（从命令行读取参数）。
    输出：
        argparse.Namespace，包含解析后的参数。
    作用：
        统一管理 V1 命令行参数定义。
    设计原因：
        参数解析与业务逻辑解耦，便于后续扩展更多开关。
    """
    parser = argparse.ArgumentParser(description="V1 项目结构扫描器")
    parser.add_argument("--repo", required=True, help="待分析的本地项目路径")
    parser.add_argument("--ask", help="V1.5 project question")
    return parser.parse_args()


def main() -> None:
    """
    输入：
        无（使用 parse_args 获取参数）。
    输出：
        无（将报告打印到标准输出）。
    作用：
        执行 V1 完整扫描流程并输出报告。
    设计原因：
        作为程序入口，保持流程清晰：解析参数 -> 扫描 -> 渲染 -> 输出。
    """
    args = parse_args()
    scan_result = run_v1_scan(args.repo)

    if args.ask:
        answer = answer_project_question(scan_result, args.ask)
        print(answer)
        return

    report = generate_v1_report(scan_result)
    print(report)


if __name__ == "__main__":
    main()
