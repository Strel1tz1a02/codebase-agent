from __future__ import annotations

from collections.abc import Callable

from src.runtime.session import Session
from src.runtime.memory import SessionMemory


AgentRunner = Callable[[dict[str, object]], dict[str, object]]


class AgentRuntime:
    """
    输入：
        memory：SessionMemory
    输出：
        AgentRuntime 对象。
    作用：
        作为 Agent 会话运行入口，统一管理 session 创建和用户提问。
    设计原因：
        controller 和 graph 是一次性 runner；Runtime 负责把多轮状态保存起来。
    """

    def __init__(
        self,
        memory: SessionMemory | None = None,
        agent_runner: AgentRunner | None = None,
    ) -> None:
        """
        输入：
            memory：可选的 session memory。
            agent_runner：可选的 Agent 执行函数。
        输出：
            无。
        作用：
            保存 Runtime 依赖的 session memory 和 Agent runner。
        设计原因：
            允许测试传入 memory 和 fake runner，后续再替换为真实 run_agent_graph。
        """
        self.memory = memory or SessionMemory()
        self.agent_runner = agent_runner

    def create_session(self, repo_path: str) -> Session:
        """
        输入：
            repo_path：当前 session 要分析的代码仓库路径。
        输出：
            Session：新创建的会话对象。
        作用：
            创建一个绑定仓库路径的 Runtime 会话。
        设计原因：
            用户后续所有追问都需要通过 session_id 找回同一个上下文。
        """
        return self.memory.create_session(repo_path)

    def ask(self, session_id: str, question: str) -> dict[str, object]:
        """
        输入：
            session_id：已有会话 ID。
            question：用户本轮问题。
        输出：
            dict：Runtime 结果，包含 session_id、status、question、answer、reason 和 message_count。
        作用：
            把用户问题追加进 session.messages，调用 Agent runner 获取回答，更新 session 
        设计原因：
            Runtime 需要成为“保存会话状态”和“调用 Agent runner”之间的边界。
        """
        session = self.memory.get_session(session_id)
        session.append_message("user", question)

        result: dict[str, object] = {
            "session_id": session.session_id,
            "status": session.status,
            "question": question,
            "message_count": len(session.messages),
        }
        if self.agent_runner is None:
            return result

        runner_result = self.agent_runner(
            {
                "question": question,
                "repo_path": session.repo_path,
                "messages": session.message_dicts,
            }
        )
        status = str(runner_result.get("status", "stopped"))
        answer = str(runner_result.get("answer", ""))
        reason = str(runner_result.get("reason", ""))

        session.status = status  # type: ignore[assignment]
        if answer:
            session.append_message("assistant", answer)

        trace_payload = {
            "status": status,
            "answer": answer,
            "reason": reason,
        }
        session.append_trace(trace_payload)

        result.update(
            {
                "status": status,
                "answer": answer,
                "message_count": len(session.messages),
            }
        )
        if reason:
            result["reason"] = reason
        return result
