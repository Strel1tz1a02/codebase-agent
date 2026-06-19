from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "payload": self.payload,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> RunEvent:
        event_payload = payload.get("payload", {})
        if not isinstance(event_payload, dict):
            event_payload = {}
        return cls(
            event_id=str(payload.get("event_id", "")),
            event_type=str(payload.get("event_type", "")),
            payload=event_payload,
        )
