from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.core.ignore import should_ignore_dir, should_ignore_file
from src.core.paths import iter_repo_files
from src.rag.indexing import build_project_index
from src.rag.retrieval import retrieve_from_index


SEARCHABLE_SUFFIXES = {".py", ".md", ".txt", ".json"}
SEARCH_SCOPES = {"src", "tests", "docs", "all"}
ENTRY_CANDIDATE_NAMES = {"main.py", "app.py", "__main__.py", "manage.py", "run.py"}
KEY_DIR_NAMES = {"src", "tests", "docs", "config", "scripts"}


class RepoSummaryInput(BaseModel):
    repo_path: str = Field(default="", description="Repository root path.")


class SearchCodeInput(BaseModel):
    repo_path: str = Field(default="", description="Repository root path.")
    keyword: str = Field(default="", description="Keyword to search for.")
    scope: str = Field(default="src", description="Search scope: src, tests, docs, or all.")
    limit: int = Field(default=20, description="Maximum number of matches.")


class RetrieveCodeInput(BaseModel):
    repo_path: str = Field(default="", description="Repository root path.")
    query: str = Field(default="", description="Semantic retrieval query.")
    top_k: int = Field(default=5, description="Maximum number of retrieved chunks.")


def _build_file_tree(files: list[Path], root: Path) -> str:
    tree: dict[str, object] = {}
    for file_path in files:
        try:
            rel = file_path.relative_to(root).as_posix()
        except ValueError:
            continue
        parts = rel.split("/")
        cursor = tree
        for index, part in enumerate(parts):
            if index == len(parts) - 1:
                cursor.setdefault("__files__", []).append(part)  # type: ignore[attr-defined]
            else:
                cursor = cursor.setdefault(part, {})  # type: ignore[attr-defined]

    def _render(node: dict[str, object], indent: int = 0) -> list[str]:
        prefix = "  " * indent
        lines: list[str] = []
        dirs = sorted(key for key in node if key != "__files__")
        for directory in dirs:
            lines.append(f"{prefix}{directory}/")
            lines.extend(_render(node[directory], indent + 1))  # type: ignore[arg-type]
        for file_name in sorted(node.get("__files__", [])):
            lines.append(f"{prefix}  {file_name}")
        return lines

    return "\n".join(_render(tree))


def repo_summary(repo_path: str) -> dict[str, object]:
    if not repo_path.strip():
        raise ValueError("repo_path is required")

    root = Path(repo_path).resolve()
    kept_files = _scan_repo_files(root)

    return {
        "repo_path": str(root),
        "file_count": len(kept_files),
        "file_types": _count_file_types(kept_files),
        "key_dirs": _summarize_key_dirs(kept_files, root),
        "entry_candidates": _find_entry_candidates(kept_files, root),
        "tree": _build_file_tree(kept_files, root),
    }


def _scan_repo_files(root: Path) -> list[Path]:
    return iter_repo_files(
        str(root),
        should_ignore_dir=should_ignore_dir,
        should_ignore_file=should_ignore_file,
    )


def _count_file_types(files: list[Path]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for file_path in files:
        suffix = file_path.suffix.lower() or "[no_suffix]"
        counts[suffix] = counts.get(suffix, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _summarize_key_dirs(files: list[Path], root: Path) -> list[str]:
    key_dirs: set[str] = set()
    for file_path in files:
        try:
            relative_path = file_path.relative_to(root)
        except ValueError:
            continue
        if len(relative_path.parts) < 2:
            continue
        top_dir = relative_path.parts[0]
        if top_dir.lower() in KEY_DIR_NAMES:
            key_dirs.add(top_dir)
    return sorted(key_dirs)


def _find_entry_candidates(files: list[Path], root: Path) -> list[str]:
    src_candidates: list[str] = []
    other_candidates: list[str] = []
    for file_path in files:
        if file_path.name not in ENTRY_CANDIDATE_NAMES:
            continue
        try:
            relative_path_obj = file_path.relative_to(root)
        except ValueError:
            continue
        relative_path = relative_path_obj.as_posix()
        if "src" in {part.lower() for part in relative_path_obj.parts}:
            src_candidates.append(relative_path)
        else:
            other_candidates.append(relative_path)

    return sorted(src_candidates) + sorted(other_candidates)


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


def search_code(
    repo_path: str,
    keyword: str,
    scope: str = "src",
    limit: int = 20,
) -> dict[str, object]:
    repo_path = repo_path.strip()
    keyword = keyword.strip()
    scope = scope.strip() or "src"

    if not repo_path:
        raise ValueError("repo_path is required")
    if not keyword:
        raise ValueError("keyword is required")
    if scope not in SEARCH_SCOPES:
        raise ValueError("scope must be one of: all, docs, src, tests")

    root = Path(repo_path).resolve()
    max_matches = max(0, limit)
    matches: list[dict[str, object]] = []

    kept_files = _scan_repo_files(root)
    for file_path in kept_files:
        if file_path.suffix.lower() not in SEARCHABLE_SUFFIXES:
            continue

        try:
            relative_path = file_path.relative_to(root).as_posix()
        except ValueError:
            continue
        if not _path_matches_search_scope(relative_path, scope):
            continue

        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
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


def retrieve_code(
    repo_path: str,
    query: str,
    top_k: int = 5,
) -> dict[str, object]:
    repo_path = repo_path.strip()
    query = query.strip()

    if not repo_path:
        raise ValueError("repo_path is required")
    if not query:
        raise ValueError("query is required")

    limit = max(0, top_k)
    if limit == 0:
        return {"query": query, "top_k": limit, "matches": []}

    project_id = Path(repo_path).name
    index = build_project_index(project_id, repo_path)
    hits = [hit.to_dict() for hit in retrieve_from_index(index, query, limit)]
    return {
        "query": query,
        "top_k": limit,
        "matches": hits,
    }


repo_summary_tool = StructuredTool.from_function(
    func=repo_summary,
    name="repo_summary",
    description=(
        "Summarize a repository before deeper inspection. Returns the normalized repo_path, file_count, "
        "file_types, key top-level directories, likely entry point files, and a safe relative file tree. "
        "Use this first when you need orientation before searching or reading specific files. "
        "Argument: repo_path is the repository root."
    ),
    args_schema=RepoSummaryInput,
)

search_code_tool = StructuredTool.from_function(
    func=search_code,
    name="search_code",
    description=(
        "Search UTF-8 code and documentation files by exact keyword inside a repository. Use this to "
        "locate files, symbols, or text before calling read_file. Arguments: repo_path is the repository "
        "root; keyword is required; scope is one of src, tests, docs, or all; limit caps the number of "
        "matches returned."
    ),
    args_schema=SearchCodeInput,
)

retrieve_code_tool = StructuredTool.from_function(
    func=retrieve_code,
    name="retrieve_code",
    description=(
        "Retrieve semantically relevant code snippets using the RAG pipeline. Use this when exact keyword "
        "search is insufficient or the question is phrased conceptually. Arguments: repo_path is the "
        "repository root; query describes what to find; top_k caps the number of snippets returned."
    ),
    args_schema=RetrieveCodeInput,
)
