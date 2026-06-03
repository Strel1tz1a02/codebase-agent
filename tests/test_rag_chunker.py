from __future__ import annotations

import unittest

from src.rag.chunker import chunk_code_file, chunk_code_files


class TestRagChunker(unittest.TestCase):
    def test_python_top_level_def_generates_chunk(self) -> None:
        record = {
            "file_path": "C:\\repo\\a.py",
            "relative_path": "a.py",
            "content": "def foo():\n    return 1\n\n\ndef bar():\n    return 2\n",
        }
        chunks = chunk_code_file(record, max_chars=2000)
        ids = [str(item["id"]) for item in chunks]
        self.assertIn("a.py:1:2", ids)
        self.assertIn("a.py:5:6", ids)

    def test_python_top_level_class_generates_chunk(self) -> None:
        record = {
            "file_path": "C:\\repo\\a.py",
            "relative_path": "a.py",
            "content": "class A:\n    def x(self):\n        return 1\n",
        }
        chunks = chunk_code_file(record, max_chars=2000)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["id"], "a.py:1:3")

    def test_non_python_file_splits_by_max_chars(self) -> None:
        record = {
            "file_path": "C:\\repo\\a.md",
            "relative_path": "a.md",
            "content": "line1\nline2\nline3\nline4\n",
        }
        chunks = chunk_code_file(record, max_chars=10)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["start_line"], 1)
        self.assertEqual(chunks[0]["end_line"], 1)

    def test_long_python_chunk_is_split_again(self) -> None:
        record = {
            "file_path": "C:\\repo\\a.py",
            "relative_path": "a.py",
            "content": "def foo():\n    x = '1234567890'\n    y = '1234567890'\n    z = '1234567890'\n",
        }
        chunks = chunk_code_file(record, max_chars=25)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(all(str(item["id"]).startswith("a.py:") for item in chunks))

    def test_chunk_has_required_fields_and_stable_id(self) -> None:
        record = {
            "file_path": "C:\\repo\\a.txt",
            "relative_path": "a.txt",
            "content": "one\ntwo\n",
        }
        chunks = chunk_code_file(record, max_chars=2000)
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        for key in ("id", "file_path", "relative_path", "start_line", "end_line", "content"):
            self.assertIn(key, chunk)
        self.assertEqual(chunk["id"], "a.txt:1:2")
        self.assertEqual(chunk["start_line"], 1)
        self.assertEqual(chunk["end_line"], 2)

    def test_empty_file_generates_no_chunk(self) -> None:
        record = {
            "file_path": "C:\\repo\\empty.py",
            "relative_path": "empty.py",
            "content": "",
        }
        self.assertEqual(chunk_code_file(record), [])

    def test_chunk_code_files_keeps_file_and_line_order(self) -> None:
        files = [
            {
                "file_path": "C:\\repo\\a.txt",
                "relative_path": "a.txt",
                "content": "a1\na2\n",
            },
            {
                "file_path": "C:\\repo\\b.txt",
                "relative_path": "b.txt",
                "content": "b1\nb2\n",
            },
        ]
        chunks = chunk_code_files(files, max_chars=3)
        self.assertEqual(chunks[0]["relative_path"], "a.txt")
        self.assertEqual(chunks[-1]["relative_path"], "b.txt")


if __name__ == "__main__":
    unittest.main()
