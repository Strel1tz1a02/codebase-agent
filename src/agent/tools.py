from __future__ import annotations

from pathlib import Path

from src.agent.schemas import ToolResult
from src.tools.file_tools import run_v1_scan, scan_files


SEARCHABLE_SUFFIXES = {".py", ".md", ".txt", ".json"}
SEARCH_SCOPES = {"src", "tests", "docs", "all"}


def repo_summary(arguments: dict[str, object]) -> dict[str, object]:
    repo_path = str(arguments.get("repo_path", "")).strip()
    if not repo_path:
        raise ValueError("repo_path is required")

    scan_result = run_v1_scan(repo_path)
    root = Path(str(scan_result["repo_path"]))

    entry_candidates: list[str] = []
    raw_entry_candidates = scan_result.get("entry_candidates", [])
    if isinstance(raw_entry_candidates, list):
        for item in raw_entry_candidates:
            if not isinstance(item, str):
                continue
            entry_path = Path(item)
            try:
                entry_candidates.append(entry_path.resolve().relative_to(root).as_posix())
            except ValueError:
                entry_candidates.append(str(entry_path))

    return {
        "repo_path": str(root),
        "file_count": int(scan_result.get("file_count", 0)),
        "file_types": scan_result.get("file_types", {}),
        "key_dirs": scan_result.get("key_dirs", []),
        "entry_candidates": entry_candidates,
    }


def read_file(arguments: dict[str, object]) -> dict[str, object]:
    repo_path = str(arguments.get("repo_path", "")).strip()
    relative_path = str(arguments.get("path", "")).strip()
    max_chars = int(arguments.get("max_chars", 8000))

    if not repo_path:
        raise ValueError("repo_path is required")
    if not relative_path:
        raise ValueError("path is required")

    root = Path(repo_path).resolve()
    target = (root / relative_path).resolve()
    try:
        normalized_relative_path = target.relative_to(root).as_posix()
    except ValueError:
        raise ValueError("path must stay inside repo") from None

    if not target.is_file():
        raise FileNotFoundError(f"file not found: {normalized_relative_path}")

    content = target.read_text(encoding="utf-8")
    limit = max(0, max_chars)
    truncated = len(content) > limit
    if truncated:
        content = content[:limit]

    return {
        "path": normalized_relative_path,
        "content": content,
        "truncated": truncated,
    }


def _path_matches_search_scope(relative_path: str, scope: str) -> bool:
    if scope == "all":
        return True
    if scope == "src":
        return relative_path.startswith("src/")
    if scope == "tests":
        return relative_path.startswith("tests/")
    if scope == "docs":
        return relative_path.startswith("Docs/") or relative_path == "README.md"
    return False


def search_code(arguments: dict[str, object]) -> dict[str, object]:
    repo_path = str(arguments.get("repo_path", "")).strip()
    keyword = str(arguments.get("keyword", "")).strip()
    scope = str(arguments.get("scope", "src")).strip() or "src"
    limit = int(arguments.get("limit", 20))

    if not repo_path:
        raise ValueError("repo_path is required")
    if not keyword:
        raise ValueError("keyword is required")
    if scope not in SEARCH_SCOPES:
        raise ValueError("scope must be one of: all, docs, src, tests")

    root = Path(repo_path).resolve()
    max_matches = max(0, limit)
    matches: list[dict[str, object]] = []

    kept_files, _ignored_paths = scan_files(str(root))
    for file_path in kept_files:
        path_obj = Path(file_path)
        if path_obj.suffix.lower() not in SEARCHABLE_SUFFIXES:
            continue

        try:
            relative_path = path_obj.resolve().relative_to(root).as_posix()
        except ValueError:
            continue
        if not _path_matches_search_scope(relative_path, scope):
            continue

        try:
            lines = path_obj.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line_text in enumerate(lines, start=1):
            if keyword not in line_text:
                continue
            matches.append(
                {
                    "path": relative_path,
                    "line": line_number,
                    "text": line_text.strip(),
                }
            )
            if len(matches) >= max_matches:
                return {
                    "keyword": keyword,
                    "scope": scope,
                    "matches": matches,
                }

    return {
        "keyword": keyword,
        "scope": scope,
        "matches": matches,
    }


TOOL_REGISTRY = {
    "repo_summary": repo_summary,
    "read_file": read_file,
    "search_code": search_code,
}


def execute_tool(tool_name: str, arguments: dict[str, object]) -> ToolResult:
    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolResult(
            ok=False,
            tool_name=tool_name,
            output={},
            error=f"unknown tool: {tool_name}",
        )

    try:
        output = tool(arguments)
    except Exception as exc:
        return ToolResult(
            ok=False,
            tool_name=tool_name,
            output={},
            error=str(exc),
        )

    return ToolResult(
        ok=True,
        tool_name=tool_name,
        output=output,
        error="",
    )
