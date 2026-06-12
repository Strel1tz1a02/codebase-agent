from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.qa import answer_project_question
from src.tools.legacy_file_tools import run_v1_scan


class TestQAFlow(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="qa_flow_test_"))
        self.repo = self.temp_dir / "demo_repo"
        self.repo.mkdir(parents=True, exist_ok=True)

        (self.repo / "src").mkdir()
        (self.repo / "README.md").write_text("# demo\n", encoding="utf-8")
        (self.repo / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        (self.repo / "src" / "main.py").write_text("print('main')\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_answer_project_question_returns_answer_and_used_files(self) -> None:
        scan_result = run_v1_scan(str(self.repo))

        with patch("src.qa.ask_llm", return_value="mocked answer") as mock_ask_llm:
            result = answer_project_question(scan_result, "入口在哪里？")

        self.assertEqual(result["answer"], "mocked answer")
        self.assertTrue(isinstance(result["used_files"], list))
        self.assertLessEqual(len(result["used_files"]), 8)
        self.assertTrue(isinstance(result["prompt"], str))
        mock_ask_llm.assert_called_once()

    def test_answer_project_question_prompt_contains_context_file_content(self) -> None:
        scan_result = run_v1_scan(str(self.repo))

        with patch("src.qa.ask_llm", side_effect=lambda prompt: prompt):
            result = answer_project_question(scan_result, "这个项目做什么？")

        prompt = str(result["prompt"])
        self.assertIn("关键文件内容：", prompt)
        self.assertIn("# demo", prompt)
        self.assertIn("print('main')", prompt)


if __name__ == "__main__":
    unittest.main()
