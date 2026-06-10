from __future__ import annotations

import unittest

from src.runtime.session import Message, Session, Trace


class TestSession(unittest.TestCase):
    def test_append_message_preserves_conversation_order(self) -> None:
        session = Session(
            session_id="session-1",
            repo_path="E:\\projects\\codebase-agent",
        )

        user_message = session.append_message("user", "Where is the entrypoint?")
        assistant_message = session.append_message("assistant", "The entrypoint is src/main.py.")

        self.assertIsInstance(user_message, Message)
        self.assertIsInstance(assistant_message, Message)
        self.assertEqual(session.messages, [user_message, assistant_message])
        self.assertEqual(session.messages[0].role, "user")
        self.assertEqual(session.messages[1].role, "assistant")

    def test_append_message_rejects_unknown_role(self) -> None:
        session = Session(
            session_id="session-1",
            repo_path="E:\\projects\\codebase-agent",
        )

        with self.assertRaises(ValueError):
            session.append_message("system", "hidden prompt")

    def test_append_trace_records_runtime_history(self) -> None:
        session = Session(
            session_id="session-1",
            repo_path="E:\\projects\\codebase-agent",
        )

        trace = session.append_trace({"status": "completed"})

        self.assertIsInstance(trace, Trace)
        self.assertEqual(session.trace, [trace])
        self.assertEqual(trace.payload, {"status": "completed"})

    def test_message_to_dict_returns_plain_dict_snapshot(self) -> None:
        message = Message(role="user", content="Where is the entrypoint?")

        message_dict = message.to_dict()
        message_dict["content"] = "changed outside"

        self.assertEqual(
            message_dict,
            {"role": "user", "content": "changed outside"},
        )
        self.assertEqual(message.content, "Where is the entrypoint?")

    def test_trace_to_dict_returns_plain_dict_snapshot(self) -> None:
        trace = Trace(payload={"status": "completed"})

        trace_dict = trace.to_dict()
        trace_dict["status"] = "failed"

        self.assertEqual(trace_dict, {"status": "failed"})
        self.assertEqual(trace.payload, {"status": "completed"})

    def test_session_dict_properties_return_plain_snapshots(self) -> None:
        session = Session(
            session_id="session-1",
            repo_path="E:\\projects\\codebase-agent",
        )
        session.append_message("user", "Where is the entrypoint?")
        session.append_trace({"status": "completed"})

        message_dicts = session.message_dicts
        trace_dicts = session.trace_dicts
        message_dicts[0]["content"] = "changed outside"
        trace_dicts[0]["status"] = "failed"

        self.assertEqual(
            message_dicts,
            [{"role": "user", "content": "changed outside"}],
        )
        self.assertEqual(trace_dicts, [{"status": "failed"}])
        self.assertEqual(session.messages[0].content, "Where is the entrypoint?")
        self.assertEqual(session.trace[0].payload, {"status": "completed"})


if __name__ == "__main__":
    unittest.main()
