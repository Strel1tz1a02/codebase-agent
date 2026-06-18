from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.runtime.events import RunEvent


@dataclass
class Run:
    """
    输入：
        run_id：run 唯一标识。
        session_id：run 所属 session。
        question：本次用户问题。
        status：run 当前状态。
        answer：graph 生成的最终回答。
        reason：失败或停止原因。
        events：run 拥有的事件列表。
    输出：
        Run 数据对象。
    作用：
        表示用户一次提问对应的一次 graph 执行。
    为什么需要这个类：
        成熟 Runtime 需要把“提问”和“执行过程”显式建模，便于查询状态、记录事件和后续支持异步执行。
    """

    run_id: str
    session_id: str = ""
    question: str = ""
    status: Literal["queued", "running", "completed", "failed", "stopped"] = "queued"
    answer: str = ""
    reason: str = ""
    events: list[RunEvent] = field(default_factory=list)

    def add_event(self, event: RunEvent) -> None:
        """把一条运行事件追加到当前 run。"""
        self.events.append(event)

    def list_events(self) -> list[RunEvent]:
        """返回当前 run 的事件快照，避免调用方直接改内部列表。"""
        return list(self.events)
