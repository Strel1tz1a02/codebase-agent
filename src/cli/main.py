from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import uvicorn

from src.runtime.runs import RuntimeService


def main(
    argv: Sequence[str] | None = None,# Sequence：表示一个元素类型为 str 的序列，可以是列表、元组等。
    runtime: RuntimeService | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    runtime = runtime or RuntimeService() # 如果调用 main 函数时没有提供 runtime 参数，就创建一个新的 RuntimeService 实例。

    if args.command == "index":
        return _run_index(args, runtime)
    if args.command == "ask":
        return _run_ask(args, runtime)
    if args.command == "serve":
        uvicorn.run("src.api.app:app", host=args.host, port=args.port)# uvicorn 是一个用于运行 Python Web 应用的 ASGI 服务器，这里指定了要运行的应用是 src.api.app 模块中的 app 对象，监听指定的 host 和 port。
        return 0

    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codebase-agent")
    subparsers = parser.add_subparsers(dest="command")# dest:指定了子命令的名称将被存储在 args 对象中的哪个属性中，这里是 "command"。

    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("--repo", required=True)
    index_parser.add_argument("--project", default="")

    ask_parser = subparsers.add_parser("ask")
    ask_parser.add_argument("--project", required=True)
    ask_parser.add_argument("question")

    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    return parser


def _run_index(args: argparse.Namespace, runtime: RuntimeService) -> int:
    repo_path = str(args.repo)
    project_name = str(args.project or Path(repo_path).name)
    project = runtime.create_project(project_name, repo_path)
    project = runtime.index_project(project.project_id)
    _print_json(
        {
            "project_id": project.project_id,
            "name": project.name,
            "repo_path": project.repo_path,
            "index_status": project.index_status,
        }
    )
    return 0


def _run_ask(args: argparse.Namespace, runtime: RuntimeService) -> int:
    project_id = str(args.project)
    session = runtime.create_session(project_id)
    run = runtime.ask(project_id, session.session_id, str(args.question))
    _print_json(
        {
            "run_id": run.run_id,
            "session_id": run.session_id,
            "status": run.status,
            "answer": run.answer,
            "reason": run.reason,
        }
    )
    return 0


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False))
