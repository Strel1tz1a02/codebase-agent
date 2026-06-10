from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, cast


@dataclass
class Message:
    """
    输入：
        role：消息角色，目前使用 user 或 assistant。
        content：消息正文。
    输出：
        Message 对象。
    作用：
        记录一次会话中的用户问题或 Agent 回答。
    设计原因：
        V6 需要支持多轮对话，必须先有一个稳定的数据结构保存历史消息。
    """

    role: Literal["user", "assistant"]
    content: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "content": self.content,
        }


@dataclass
class Trace:
    """
    输入：
        payload：事件详情字典。
    输出：
        Trace 对象。
    作用：
        保存一次 Agent 运行后的摘要。
    设计原因：
        V6 当前只有一种 trace 事件，保留 payload 即可，避免过早设计事件类型体系。
    """

    payload: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


@dataclass
class Session:
    """
    输入：
        session_id：会话唯一 ID。
        repo_path：当前会话绑定的代码仓库路径。
        messages：多轮对话消息列表。
        trace：结构化运行事件列表。
        status：当前会话状态。
    输出：
        Session 对象。
    作用：
        表示围绕一个代码仓库展开的一次多轮 Agent 会话。
    设计原因：
        一次性 runner 每次调用都会丢失上下文；Session 是升级为 Runtime 的基础。
    """

    session_id: str
    repo_path: str
    messages: list[Message] = field(default_factory=list)
    trace: list[Trace] = field(default_factory=list)
    status: Literal["running", "completed", "failed", "stopped"] = "running"

    @property # property 装饰器把方法变成属性，调用时不需要加括号。
    def message_dicts(self) -> list[dict[str, str]]:
        return [message.to_dict() for message in self.messages]

    @property
    def trace_dicts(self) -> list[dict[str, object]]:
        return [event.to_dict() for event in self.trace]

    def append_message(self, role: str, content: str) -> Message:
        """
        输入：
            role：消息角色，必须是 user 或 assistant。
            content：消息正文。
        输出：
            Message：追加后的消息对象。
        作用：
            把一条对话消息追加到当前 Session。
        设计原因：
            messages 是 Session 自己的内部状态，追加消息的规则应该靠近数据本身。
        """
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        message = Message(
            role=cast(Literal["user", "assistant"], role),
            content=content,
        )
        self.messages.append(message)
        return message

    def append_trace(
        self,
        payload: dict[str, object],
    ) -> Trace:
        """
        输入：
            payload：事件详情。
        输出：
            Trace：追加后的 trace 对象。
        作用：
            把一条结构化运行事件追加到当前 Session。
        设计原因：
            trace 也是 Session 的内部历史，追加逻辑放在 Session 层更清楚。
        """
        event = Trace(payload=payload)
        self.trace.append(event)
        return event
