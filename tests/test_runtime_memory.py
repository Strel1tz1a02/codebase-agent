from __future__ import annotations

import unittest

from src.runtime.session import Message, Trace
from src.runtime.memory import SessionMemory


class TestSessionMemory(unittest.TestCase):
    def test_create_session_returns_empty_session_bound_to_repo(self) -> None:
        memory = SessionMemory()

        session = memory.create_session("E:\\projects\\codebase-agent")

        self.assertTrue(session.session_id)
        self.assertEqual(session.repo_path, "E:\\projects\\codebase-agent")
        self.assertEqual(session.messages, [])
        self.assertEqual(session.trace, [])
        self.assertEqual(session.status, "running")

    def test_get_session_returns_existing_session(self) -> None:
        memory = SessionMemory()
        created = memory.create_session("E:\\projects\\codebase-agent")

        loaded = memory.get_session(created.session_id)

        self.assertIs(loaded, created)

    def test_get_session_raises_for_unknown_session_id(self) -> None:
        memory = SessionMemory()

        with self.assertRaises(KeyError):
            memory.get_session("missing-session")

    def test_memory_does_not_expose_append_message(self) -> None:
        memory = SessionMemory()

        self.assertFalse(hasattr(memory, "append_message"))

    def test_memory_does_not_expose_append_trace_event(self) -> None:
        memory = SessionMemory()

        self.assertFalse(hasattr(memory, "append_trace_event"))


if __name__ == "__main__":
    unittest.main()
