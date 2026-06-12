from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from src.tools.legacy_file_tools import (
    build_file_tree,
    count_file_types,
    find_entry_candidates,
    read_context_files,
    run_v1_scan,
    scan_files,
    select_context_files,
    summarize_key_dirs,
)


class TestV1FileTools(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="v1_scan_test_"))
        self.repo = self.temp_dir / "demo_repo"
        self.repo.mkdir(parents=True, exist_ok=True)

        # 业务目录和文件
        (self.repo / "src").mkdir()
        (self.repo / "src" / "core").mkdir()
        (self.repo / "tests").mkdir()
        (self.repo / "docs").mkdir()
        (self.repo / "config").mkdir()
        (self.repo / "scripts").mkdir()
        (self.repo / "data" / "raw").mkdir(parents=True)

        (self.repo / "README.md").write_text("# demo\n", encoding="utf-8")
        (self.repo / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        (self.repo / "src" / "main.py").write_text("print('main')\n", encoding="utf-8")
        (self.repo / "src" / "__main__.py").write_text("print('run')\n", encoding="utf-8")
        (self.repo / "src" / "core" / "service.py").write_text("def run(): pass\n", encoding="utf-8")
        (self.repo / "tests" / "test_main.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
        (self.repo / "docs" / "architecture.md").write_text("# arch\n", encoding="utf-8")
        (self.repo / "config" / "settings.yaml").write_text("env: dev\n", encoding="utf-8")
        (self.repo / "scripts" / "build.ps1").write_text("echo build\n", encoding="utf-8")
        (self.repo / "data" / "raw" / "sample.json").write_text('{"id":1}\n', encoding="utf-8")

        # 应忽略目录和文件
        (self.repo / ".git").mkdir()
        (self.repo / ".venv").mkdir()
        (self.repo / "node_modules").mkdir()
        (self.repo / "__pycache__").mkdir()
        (self.repo / "src" / "junk.pyc").write_text("x", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_files_filters_ignored_paths(self) -> None:
        kept_files, ignored_paths = scan_files(str(self.repo))

        self.assertTrue(any(path.endswith("src\\main.py") for path in kept_files))
        self.assertFalse(any(path.endswith("junk.pyc") for path in kept_files))
        self.assertTrue(any(path.endswith("\\.git") for path in ignored_paths))
        self.assertTrue(any(path.endswith("\\node_modules") for path in ignored_paths))

    def test_count_file_types(self) -> None:
        kept_files, _ = scan_files(str(self.repo))
        file_types = count_file_types(kept_files)
        self.assertEqual(file_types[".py"], 4)
        self.assertEqual(file_types[".md"], 2)
        self.assertEqual(file_types[".yaml"], 1)

    def test_find_entry_candidates(self) -> None:
        kept_files, _ = scan_files(str(self.repo))
        candidates = find_entry_candidates(kept_files)
        self.assertTrue(any(path.endswith("src\\main.py") for path in candidates))
        self.assertTrue(any(path.endswith("src\\__main__.py") for path in candidates))

    def test_summarize_key_dirs_uses_repo_top_level(self) -> None:
        kept_files, _ = scan_files(str(self.repo))
        key_dirs = summarize_key_dirs(kept_files, str(self.repo))
        self.assertIn("src", key_dirs)
        self.assertIn("tests", key_dirs)
        self.assertIn("docs", key_dirs)
        self.assertIn("config", key_dirs)
        self.assertIn("scripts", key_dirs)

    def test_build_file_tree_contains_expected_sections(self) -> None:
        kept_files, _ = scan_files(str(self.repo))
        tree = build_file_tree(kept_files, str(self.repo))
        self.assertIn("demo_repo/", tree)
        self.assertIn("src/", tree)
        self.assertIn("main.py", tree)

    def test_run_v1_scan_has_required_keys(self) -> None:
        result = run_v1_scan(str(self.repo))
        required_keys = {
            "repo_path",
            "tree",
            "file_count",
            "file_types",
            "key_dirs",
            "entry_candidates",
            "ignored_paths",
        }
        self.assertTrue(required_keys.issubset(set(result.keys())))

    def test_select_context_files_prefers_root_and_src_files(self) -> None:
        result = run_v1_scan(str(self.repo))
        selected = select_context_files(result, str(self.repo))

        self.assertGreaterEqual(len(selected), 3)
        self.assertEqual(selected[0], str((self.repo / "README.md").resolve()))
        self.assertEqual(selected[1], str((self.repo / "requirements.txt").resolve()))
        self.assertEqual(selected[2], str((self.repo / "src" / "main.py").resolve()))

    def test_select_context_files_skips_missing_candidates(self) -> None:
        result = run_v1_scan(str(self.repo))
        result["entry_candidates"] = [
            str(self.repo / "missing.py"),
            str(self.repo / "src" / "main.py"),
        ]

        selected = select_context_files(result, str(self.repo))

        self.assertFalse(any(path.endswith("missing.py") for path in selected))
        self.assertIn(str((self.repo / "src" / "main.py").resolve()), selected)

    def test_select_context_files_respects_max_files(self) -> None:
        result = run_v1_scan(str(self.repo))
        selected = select_context_files(result, str(self.repo), max_files=2)

        self.assertLessEqual(len(selected), 2)

    def test_read_context_files_reads_content(self) -> None:
        readme = self.repo / "README.md"

        contents = read_context_files([str(readme)])

        self.assertEqual(contents[str(readme.resolve())], "# demo\n")

    def test_read_context_files_truncates_long_files(self) -> None:
        long_file = self.repo / "long.txt"
        long_file.write_text("abcdef", encoding="utf-8")

        contents = read_context_files([str(long_file)], max_chars_per_file=3)

        self.assertEqual(contents[str(long_file.resolve())], "abc")

    def test_read_context_files_skips_missing_files(self) -> None:
        missing_file = self.repo / "missing.txt"

        contents = read_context_files([str(missing_file)])

        self.assertEqual(contents, {})

    def test_read_context_files_deduplicates_same_resolved_path(self) -> None:
        readme_abs = self.repo / "README.md"
        readme_rel = self.repo / "." / "README.md"

        contents = read_context_files([str(readme_abs), str(readme_rel)])

        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[str(readme_abs.resolve())], "# demo\n")


if __name__ == "__main__":
    unittest.main()
