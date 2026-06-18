from __future__ import annotations

from src.runtime.events import RunEvent
from src.runtime.project import Project
from src.runtime.session import RuntimeSession

__all__ = [
    "Project",
    "Run",
    "RunEvent",
    "RuntimeService",
    "RuntimeSession",
]


def __getattr__(name: str) -> object:
    """按需导出较重的 runtime 对象，避免导入轻量子模块时加载模型依赖。"""
    if name in {"Run", "RuntimeService"}:
        from src.runtime.run import Run
        from src.runtime.service import RuntimeService

        return {"Run": Run, "RuntimeService": RuntimeService}[name]
    raise AttributeError(f"module 'src.runtime' has no attribute {name!r}")

