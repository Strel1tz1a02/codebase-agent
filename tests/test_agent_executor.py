from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.tools.registry import TOOL_REGISTRY, execute_tool


class TestAgentExecutor(unittest.TestCase):
    def test_tool_registry_does_not_include_stub_tools(self) -> None:
        self.assertNotIn("tool_stub_a", TOOL_REGISTRY)
        self.assertNotIn("tool_stub_b", TOOL_REGISTRY)

    def test_registered_tool_executes_successfully(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        result = execute_tool("repo_summary", {"repo_path": repo_path})

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "repo_summary")
        self.assertEqual(result.error, "")
        self.assertIn("src/main.py", result.output["entry_candidates"])

    def test_repo_summary_returns_basic_repository_facts(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool("repo_summary", {"repo_path": repo_path})

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "repo_summary")
        self.assertEqual(result.error, "")
        self.assertEqual(result.output["repo_path"], repo_path)
        self.assertGreaterEqual(result.output["file_count"], 1)
        self.assertIn("src", result.output["key_dirs"])
        self.assertIn("tests", result.output["key_dirs"])
        self.assertIn("src/main.py", result.output["entry_candidates"])

    def test_read_file_returns_repository_file_content(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool(
            "read_file",
            {"repo_path": repo_path, "path": "src/main.py", "max_chars": 20000},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "read_file")
        self.assertEqual(result.error, "")
        self.assertEqual(result.output["path"], "src/main.py")
        self.assertIn("def main()", result.output["content"])
        self.assertFalse(result.output["truncated"])

    def test_read_file_rejects_path_outside_repository(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool("read_file", {"repo_path": repo_path, "path": "..\\secret.txt"})

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "read_file")
        self.assertIn("path must stay inside repo", result.error)

    def test_search_code_finds_keyword_with_path_line_and_text(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool("search_code", {"repo_path": repo_path, "keyword": "run_agent_loop"})

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "search_code")
        self.assertEqual(result.error, "")
        self.assertEqual(result.output["keyword"], "run_agent_loop")
        self.assertEqual(result.output["scope"], "src")
        self.assertLessEqual(len(result.output["matches"]), 20)
        self.assertTrue(result.output["matches"])
        self.assertTrue(
            all(str(match["path"]).startswith("src/") for match in result.output["matches"])
        )
        self.assertTrue(
            any(
                match["path"] == "src/agent/controller.py"
                and match["text"] == "def run_agent_loop("
                and isinstance(match["line"], int)
                for match in result.output["matches"]
            )
        )

    def test_search_code_returns_empty_matches_for_missing_keyword(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        missing_keyword = "__definitely_" + "absent_keyword__"

        result = execute_tool(
            "search_code",
            {"repo_path": repo_path, "keyword": missing_keyword},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "search_code")
        self.assertEqual(result.output["keyword"], missing_keyword)
        self.assertEqual(result.output["matches"], [])

    def test_search_code_can_search_tests_scope_explicitly(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool(
            "search_code",
            {"repo_path": repo_path, "keyword": "test_search_code_", "scope": "tests"},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.output["scope"], "tests")
        self.assertTrue(result.output["matches"])
        self.assertTrue(
            all(str(match["path"]).startswith("tests/") for match in result.output["matches"])
        )

    def test_search_code_can_search_all_scope_explicitly(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool(
            "search_code",
            {"repo_path": repo_path, "keyword": "run_agent_loop", "scope": "all", "limit": 100},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.output["scope"], "all")
        paths = [str(match["path"]) for match in result.output["matches"]]
        self.assertIn("src/agent/controller.py", paths)
        self.assertTrue(any(path.startswith("tests/") for path in paths))

    def test_retrieve_code_is_registered(self) -> None:
        self.assertIn("retrieve_code", TOOL_REGISTRY)

    def test_retrieve_code_returns_citable_chunks(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)
        fake_hits = [
            {
                "relative_path": "src/agent/controller.py",
                "start_line": 9,
                "end_line": 70,
                "content": "def run_agent_loop(...):\n    pass\n",
                "score": 0.91,
            }
        ]

        with patch("src.tools.codebase.retrieve_relevant_chunks", return_value=fake_hits) as mock_retrieve:
            result = execute_tool(
                "retrieve_code",
                {
                    "repo_path": repo_path,
                    "query": "How does the agent loop execute tools?",
                    "top_k": 1,
                },
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.tool_name, "retrieve_code")
        self.assertEqual(result.error, "")
        self.assertEqual(result.output["query"], "How does the agent loop execute tools?")
        self.assertEqual(result.output["top_k"], 1)
        self.assertEqual(result.output["matches"], fake_hits)
        mock_retrieve.assert_called_once_with(
            question="How does the agent loop execute tools?",
            repo_path=repo_path,
            top_k=1,
            reindex=False,
        )

    def test_retrieve_code_requires_query(self) -> None:
        repo_path = str(Path(__file__).resolve().parent.parent)

        result = execute_tool("retrieve_code", {"repo_path": repo_path})

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "retrieve_code")
        self.assertIn("query is required", result.error)

    def test_unknown_tool_returns_failed_result(self) -> None:
        result = execute_tool("missing_tool", {})

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "missing_tool")
        self.assertEqual(result.output, {})
        self.assertEqual(result.error, "unknown tool: missing_tool")

    def test_tool_exception_is_wrapped_as_failed_result(self) -> None:
        def broken_tool(arguments: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("boom")

        TOOL_REGISTRY["broken_tool"] = broken_tool
        try:
            result = execute_tool("broken_tool", {"x": 1})
        finally:
            del TOOL_REGISTRY["broken_tool"]

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "broken_tool")
        self.assertEqual(result.output, {})
        self.assertEqual(result.error, "boom")


if __name__ == "__main__":
    unittest.main()
