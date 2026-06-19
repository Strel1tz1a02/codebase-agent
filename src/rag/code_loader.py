from __future__ import annotations

from pathlib import Path

from src.core.ignore import should_ignore_dir, should_ignore_file
from src.core.paths import iter_repo_files

SUPPORTED_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
}


def load_code_files(repo_path: str) -> list[dict[str, object]]:
    root = Path(repo_path).resolve()
    file_records: list[dict[str, object]] = []

    for safe_path in iter_repo_files(
        str(root),
        should_ignore_dir=should_ignore_dir,
        should_ignore_file=should_ignore_file,
        suffixes=SUPPORTED_TEXT_SUFFIXES,
    ):
        try:
            content = safe_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        file_records.append(
            {
                "file_path": str(safe_path),
                "relative_path": str(safe_path.relative_to(root)),
                "content": content,
            }
        )

    file_records.sort(key=lambda item: str(item["relative_path"]).casefold())
    return file_records
