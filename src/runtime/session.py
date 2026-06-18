from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.core.errors import RunNotFoundError

if TYPE_CHECKING:
    from src.runtime.run import Run


@dataclass
class RuntimeSession:
    """
    输入：
        session_id：会话唯一标识。
        project_id：当前会话绑定的项目 ID。
    输出：
        RuntimeSession 数据对象。
    作用：
        表示围绕某个 project 展开的多轮对话容器。
    为什么需要这个类：
        session 把用户连续提问和同一个代码仓库绑定起来，后续 run 都从这里找到 project 上下文。
    """

    session_id: str
    runs: dict[str, Run] = field(default_factory=dict)

    def add_run(self, run: Run) -> None:
        """把一次 run 记录挂到当前 session 下。"""
        self.runs[run.run_id] = run

    def get_run(self, run_id: str) -> Run:
        """按 run_id 读取 run，不存在时抛出领域异常。"""
        if run_id not in self.runs:
            raise RunNotFoundError(f"run not found: {run_id}")
        return self.runs[run_id]
