from __future__ import annotations

import unittest

from src.runtime.session import Message, Session, Trace


class TestSession(unittest.TestCase):
    def test_append_message_preserves_conversation_order(self) -> None:
        session = Session(
            session_id="session-1",
            repo_path="E:\\projects\\codebase-agent",
        )

        user_message = session.append_message("user", "入口在哪？")
        assistant_message = session.append_message("assistant", "入口在 src/main.py。")

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

    def test_to_message_dicts_returns_plain_dict_snapshot(self) -> None:
        session = Session(
            session_id="session-1",
            repo_path="E:\\projects\\codebase-agent",
        )
        session.append_message("user", "入口在哪？")
        session.append_message("assistant", "入口在 src/main.py。")

        message_dicts = session.to_message_dicts()
        message_dicts[0]["content"] = "被外部修改"

        self.assertEqual(
            message_dicts,
            [
                {"role": "user", "content": "被外部修改"},
                {"role": "assistant", "content": "入口在 src/main.py。"},
            ],
        )
        self.assertEqual(session.messages[0].content, "入口在哪？")


if __name__ == "__main__":
    unittest.main()
