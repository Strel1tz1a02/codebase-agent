from __future__ import annotations

import io
import unittest
from argparse import Namespace
from unittest.mock import patch

from src.main import main


class TestMainChunksCLI(unittest.TestCase):
    def test_build_chunks_prints_summary_and_skips_llm_path(self) -> None:
        fake_args = Namespace(
            repo="E:\\projects\\demo_repo",
            ask=None,
            provider=None,
            model=None,
            api_key=None,
            base_url=None,
            build_chunks=True,
        )
        fake_files = [
            {
                "file_path": "E:\\projects\\demo_repo\\src\\a.py",
                "relative_path": "src\\a.py",
                "content": "def a():\n    return 1\n",
            }
        ]
        fake_chunks = [
            {
                "id": "src\\a.py:1:2",
                "file_path": "E:\\projects\\demo_repo\\src\\a.py",
                "relative_path": "src\\a.py",
                "start_line": 1,
                "end_line": 2,
                "content": "def a():\n    return 1\n",
            }
        ]

        with patch("src.main.parse_args", return_value=fake_args), patch(
            "src.main.load_code_files", return_value=fake_files
        ) as mock_loader, patch("src.main.chunk_code_files", return_value=fake_chunks) as mock_chunker, patch(
            "src.main.answer_project_question"
        ) as mock_qa, patch("src.main.configure_llm") as mock_configure_llm, patch(
            "src.main.run_v1_scan"
        ) as mock_run_v1_scan, patch("sys.stdout", new_callable=io.StringIO) as fake_stdout:
            main()

        output = fake_stdout.getvalue()
        self.assertIn("Total files: 1", output)
        self.assertIn("Total chunks: 1", output)
        self.assertIn("id: src\\a.py:1:2", output)
        self.assertIn("relative_path: src\\a.py", output)
        self.assertIn("start_line: 1", output)
        self.assertIn("end_line: 2", output)
        self.assertIn("preview: def a():\\n    return 1\\n", output)
        mock_loader.assert_called_once_with("E:\\projects\\demo_repo")
        mock_chunker.assert_called_once_with(fake_files)
        mock_qa.assert_not_called()
        mock_configure_llm.assert_not_called()
        mock_run_v1_scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
