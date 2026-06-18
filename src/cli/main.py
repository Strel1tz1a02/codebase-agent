from __future__ import annotations

import argparse
from typing import Sequence

import uvicorn


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codebase-agent")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)

    uvicorn.run("src.api.app:app", host=args.host, port=args.port)
    return 0
