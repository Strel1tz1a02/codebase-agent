from __future__ import annotations

import unittest

from src.prompts.templates import build_project_qa_prompt


class TestPromptTemplates(unittest.TestCase):
    def test_build_project_qa_prompt_with_file_contents(self) -> None:
        repo_summary = {
            "tree": "demo_repo/\n└── src/\n    └── main.py",
            "file_types": {".py": 1, ".md": 1},
            "key_dirs": ["src"],
            "entry_candidates": ["E:\\projects\\demo_repo\\src\\main.py"],
        }
        file_contents = {
            "E:\\projects\\demo_repo\\README.md": "# demo\n",
            "E:\\projects\\demo_repo\\src\\main.py": "print('hello')\n",
        }

        prompt = build_project_qa_prompt(
            repo_summary=repo_summary,
            question="入口在哪里？",
            file_contents=file_contents,
        )

        self.assertIn("关键文件内容：", prompt)
        self.assertIn("### E:\\projects\\demo_repo\\README.md", prompt)
        self.assertIn("print('hello')", prompt)
        self.assertIn("用户问题：", prompt)

    def test_build_project_qa_prompt_without_file_contents(self) -> None:
        repo_summary = {
            "tree": "demo_repo/",
            "file_types": {".py": 1},
            "key_dirs": ["src"],
            "entry_candidates": [],
        }

        prompt = build_project_qa_prompt(
            repo_summary=repo_summary,
            question="这个项目是做什么的？",
        )

        self.assertIn("[未提供关键文件内容]", prompt)
        self.assertIn("这个项目是做什么的？", prompt)


if __name__ == "__main__":
    unittest.main()
