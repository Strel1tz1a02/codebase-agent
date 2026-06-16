from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunEvent:
    """
    输入：
        event_id：事件唯一标识。
        run_id：事件所属 run。
        event_type：事件类型。
        payload：事件详情。
    输出：
        RunEvent 数据对象。
    作用：
        记录一次 run 执行过程中的关键事件。
    为什么需要这个类：
        Agent 系统需要可观察性；event 让 Runtime 可以记录 graph start、graph finish 和 graph 内部事件。
    """

    event_id: str
    event_type: str
    payload: dict[str, object] = field(default_factory=dict)

