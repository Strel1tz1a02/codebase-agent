from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from src.rag.code_loader import load_code_files


class TestRagCodeLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="rag_loader_test_"))
        self.repo = self.temp_dir / "repo"
        self.repo.mkdir()

        (self.repo / "pkg").mkdir()
        (self.repo / ".git").mkdir()
        (self.repo / ".venv").mkdir()
        (self.repo / "node_modules").mkdir()
        (self.repo / "__pycache__").mkdir()

        (self.repo / "a.py").write_text("print('a')\n", encoding="utf-8")
        (self.repo / "b.md").write_text("# title\n", encoding="utf-8")
        (self.repo / "c.toml").write_text("name='demo'\n", encoding="utf-8")
        (self.repo / "pkg" / "d.json").write_text('{"x":1}\n', encoding="utf-8")
        (self.repo / "skip.bin").write_bytes(b"\x00\x01")
        (self.repo / "pkg" / "skip.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (self.repo / ".git" / "x.py").write_text("print('x')\n", encoding="utf-8")
        (self.repo / ".venv" / "x.py").write_text("print('x')\n", encoding="utf-8")
        (self.repo / "node_modules" / "x.py").write_text("print('x')\n", encoding="utf-8")
        (self.repo / "__pycache__" / "x.py").write_text("print('x')\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_supported_text_files(self) -> None:
        records = load_code_files(str(self.repo))
        relative_paths = [str(item["relative_path"]) for item in records]
        self.assertIn("a.py", relative_paths)
        self.assertIn("b.md", relative_paths)
        self.assertIn("c.toml", relative_paths)

    def test_skip_ignored_dirs_and_unsupported_suffix(self) -> None:
        records = load_code_files(str(self.repo))
        relative_paths = [str(item["relative_path"]) for item in records]
        self.assertNotIn(".git\\x.py", relative_paths)
        self.assertNotIn(".venv\\x.py", relative_paths)
        self.assertNotIn("node_modules\\x.py", relative_paths)
        self.assertNotIn("__pycache__\\x.py", relative_paths)
        self.assertNotIn("skip.bin", relative_paths)
        self.assertNotIn("pkg\\skip.csv", relative_paths)

    def test_returns_absolute_and_relative_path(self) -> None:
        records = load_code_files(str(self.repo))
        target = next(item for item in records if str(item["relative_path"]) == "a.py")
        self.assertTrue(Path(str(target["file_path"])).is_absolute())
        self.assertEqual(str(target["relative_path"]), "a.py")
        self.assertEqual(str(target["content"]), "print('a')\n")

    def test_returns_stable_sorted_order(self) -> None:
        records = load_code_files(str(self.repo))
        relative_paths = [str(item["relative_path"]) for item in records]
        self.assertEqual(relative_paths, sorted(relative_paths, key=str.casefold))

    def test_raises_clear_error_for_missing_or_non_dir(self) -> None:
        missing = self.repo / "missing"
        with self.assertRaises(FileNotFoundError):
            load_code_files(str(missing))

        file_path = self.repo / "single.py"
        file_path.write_text("print('x')\n", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            load_code_files(str(file_path))


if __name__ == "__main__":
    unittest.main()
