from __future__ import annotations

from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.core.paths import iter_repo_files
from src.rag.indexing import build_project_index
from src.rag.retrieval import retrieve_from_index
from src.core.ignore import should_ignore_dir, should_ignore_file


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
    """将文件路径列表转为缩进目录树文本，LLM 可直接据此定位文件。"""
    tree: dict[str, object] = {}
    for file_path in files:
        try:
            rel = file_path.relative_to(root).as_posix()
        except ValueError:
            continue
        parts = rel.split("/")
        cursor = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                cursor.setdefault("__files__", []).append(part)  # type: ignore[attr-defined]
            else:
                cursor = cursor.setdefault(part, {})  # type: ignore[attr-defined]

    def _render(node: dict[str, object], indent: int = 0) -> list[str]:
        prefix = "  " * indent
        lines: list[str] = []
        dirs = sorted(k for k in node if k != "__files__")
        for d in dirs:
            lines.append(f"{prefix}{d}/")
            lines.extend(_render(node[d], indent + 1))  # type: ignore[arg-type]
        for f in sorted(node.get("__files__", [])):
            lines.append(f"{prefix}  {f}")
        return lines

    return "\n".join(_render(tree))


def repo_summary(repo_path: str) -> dict[str, object]:
    """
    输入：
        repo_path：代码仓库根目录路径。
    输出：
        dict：项目文件数量、文件类型、关键目录、入口候选和目录树。
    作用：
        将 repo_summary 包装成 LangChain tool 可调用函数。
    设计原因：
        repo_summary 是 Agent 理解代码仓库的入口工具，先用确定性扫描保证结果稳定。
    """
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
    """
    输入：
        root：已规范化的仓库根目录。
    输出：
        list[Path]：应该参与工具分析的文件路径。
    作用：
        扫描仓库并应用统一忽略规则。
    设计原因：
        repo_summary 和 search_code 需要同一套稳定文件边界，成熟入口不再依赖旧 V1 模块。
    """
    return iter_repo_files(
        str(root),
        should_ignore_dir=should_ignore_dir,
        should_ignore_file=should_ignore_file,
    )


def _count_file_types(files: list[Path]) -> dict[str, int]:
    """
    输入：
        files：已扫描的文件路径。
    输出：
        dict[str, int]：按后缀统计的文件数量。
    作用：
        给 repo_summary 返回简要的仓库文件类型分布。
    设计原因：
        工具输出需要稳定、结构化，便于 Graph 和 API 消费。
    """
    counts: dict[str, int] = {}
    for file_path in files:
        suffix = file_path.suffix.lower() or "[no_suffix]"
        counts[suffix] = counts.get(suffix, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _summarize_key_dirs(files: list[Path], root: Path) -> list[str]:
    """
    输入：
        files：已扫描的文件路径。
        root：仓库根目录。
    输出：
        list[str]：项目关键方向的顶层目录。
    作用：
        提供仓库结构的快速摘要。
    设计原因：
        repo_summary 是给 Agent 先看全局的确定性工具，不引入 LLM 不确定性。
    """
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
    """
    输入：
        files：已扫描的文件路径。
        root：仓库根目录。
    输出：
        list[str]：可能的运行入口相对路径。
    作用：
        基于常见文件名找到成熟入口候选。
    设计原因：
        这是 repo_summary 的确定性启发式信息，不应该绑定旧 CLI 文件。
    """
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
    """
    输入：
        relative_path：仓库内相对路径。
        scope：搜索范围。
    输出：
        bool：路径是否属于指定搜索范围。
    作用：
        判断文件是否应该参与关键字搜索。
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


def search_code(
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
        将 search_code 包装成 LangChain tool 可调用函数。
    设计原因：
        让 Graph 可以通过统一工具接口执行关键字搜索。
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

    kept_files = _scan_repo_files(root)
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


def retrieve_code(
    repo_path: str,
    query: str,
    top_k: int = 5,
) -> dict[str, object]:
    """语义检索代码片段：每次调用时按 repo_path 构建临时索引并检索，返回命中的代码片段。"""
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
    description="Summarize repository structure, file types, key directories, and entry candidates.",
    args_schema=RepoSummaryInput,
)

REPO_SUMMARY_DESCRIPTION = (
    "repo_summary: 了解仓库整体结构（目录树、文件数量、类型分布、关键目录、入口文件候选）\n"
    "  repo_path: 必填，仓库根目录路径\n"
    "  返回 tree 字段包含完整目录树和每个文件相对于仓库的路径，可直接据此定位到具体文件"
)

search_code_tool = StructuredTool.from_function(
    func=search_code,
    name="search_code",
    description="Search code files by keyword inside a repository.",
    args_schema=SearchCodeInput,
)

SEARCH_CODE_DESCRIPTION = (
    "search_code: 按关键字搜索代码文件中的匹配行\n"
    "  repo_path: 必填，仓库根目录路径\n"
    "  keyword: 必填，搜索关键词\n"
    "  scope: src/tests/docs/all，默认src\n"
    "  limit: 最多返回条数，默认20"
)

retrieve_code_tool = StructuredTool.from_function(
    func=retrieve_code,
    name="retrieve_code",
    description="Retrieve relevant code snippets with the existing RAG pipeline.",
    args_schema=RetrieveCodeInput,
)

RETRIEVE_CODE_DESCRIPTION = (
    "retrieve_code: 语义检索与 query 最相关的代码片段（RAG召回）\n"
    "  repo_path: 必填，仓库根目录路径\n"
    "  query: 必填，用自然语言描述你想找什么代码\n"
    "  top_k: 返回片段数，默认5"
)
