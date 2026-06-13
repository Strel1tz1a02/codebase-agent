from __future__ import annotations

from dataclasses import dataclass


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
    project_id: str

