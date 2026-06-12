from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.rag.retrieval import retrieve_relevant_chunks
from src.tools.file_tools import run_v1_scan, scan_files


SEARCHABLE_SUFFIXES = {".py", ".md", ".txt", ".json"}
SEARCH_SCOPES = {"src", "tests", "docs", "all"}


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
    reindex: bool = Field(default=False, description="Whether to rebuild the RAG index first.")


def _repo_summary(repo_path: str) -> dict[str, object]:
    """
    输入：
        repo_path：代码仓库根目录路径。
    输出：
        dict：项目文件数量、文件类型、关键目录和入口候选。
    作用：
        把旧版 repo_summary 工具包装成 LangChain tool 可调用函数。
    设计原因：
        repo_summary 是 Agent 理解代码仓库的入口工具，先用确定性扫描保证结果稳定。
    """
    if not repo_path.strip():
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


def _path_matches_search_scope(relative_path: str, scope: str) -> bool:
    """
    输入：
        relative_path：仓库内相对路径。
        scope：搜索范围。
    输出：
        bool：路径是否属于该搜索范围。
    作用：
        判断目录是否应该参与关键词搜索。
    设计原因：
        search_code 需要支持 src、tests、docs、all 几种常用范围。
    """
    if scope == "all":
        return True
    if scope == "src":
        return relative_path.startswith("src/")
    if scope == "tests":
        return relative_path.startswith("tests/")
    if scope == "docs":
        return relative_path.startswith("Docs/") or relative_path == "README.md"
    return False


def _search_code(
    repo_path: str,
    keyword: str,
    scope: str = "src",
    limit: int = 20,
) -> dict[str, object]:
    """
    输入：
        repo_path：代码仓库根目录路径。
        keyword：要搜索的关键字。
        scope：搜索范围，默认 src。
        limit：最多返回多少条匹配。
    输出：
        dict：包含 keyword、scope 和 matches。
    作用：
        把旧版 search_code 工具包装成 LangChain tool 可调用函数。
    设计原因：
        让 Graph 后续可以通过统一工具接口执行关键词搜索。
    """
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


def _retrieve_code(
    repo_path: str,
    query: str,
    top_k: int = 5,
    reindex: bool = False,
) -> dict[str, object]:
    """
    输入：
        repo_path：代码仓库根目录路径。
        query：语义检索问题。
        top_k：最多返回多少条代码片段。
        reindex：是否强制重建索引。
    输出：
        dict：包含 query、top_k 和 matches。
    作用：
        把旧版 retrieve_code 工具包装成 LangChain tool 可调用函数。
    设计原因：
        让后续 Agent 可以通过 tool calling 触发 RAG 检索。
    """
    repo_path = repo_path.strip()
    query = query.strip()

    if not repo_path:
        raise ValueError("repo_path is required")
    if not query:
        raise ValueError("query is required")

    limit = max(0, top_k)
    matches = retrieve_relevant_chunks(
        question=query,
        repo_path=repo_path,
        top_k=limit,
        reindex=reindex,
    )
    return {
        "query": query,
        "top_k": limit,
        "matches": matches,
    }


repo_summary_tool = StructuredTool.from_function(
    func=_repo_summary,
    name="repo_summary",
    description="Summarize repository structure, file types, key directories, and entry candidates.",
    args_schema=RepoSummaryInput,
)

search_code_tool = StructuredTool.from_function(
    func=_search_code,
    name="search_code",
    description="Search code files by keyword inside a repository.",
    args_schema=SearchCodeInput,
)

retrieve_code_tool = StructuredTool.from_function(
    func=_retrieve_code,
    name="retrieve_code",
    description="Retrieve relevant code snippets with the existing RAG pipeline.",
    args_schema=RetrieveCodeInput,
)
