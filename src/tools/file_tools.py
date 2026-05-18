from __future__ import annotations

from pathlib import Path

from src.utils.ignore import should_ignore_dir, should_ignore_file

# V1 默认入口文件名：用于基于规则识别项目可能的启动入口。
DEFAULT_ENTRY_CANDIDATE_NAMES = {
    "main.py",
    "app.py",
    "__main__.py",
    "manage.py",
    "run.py",
}

# V1 主要目录候选：用于从扫描结果中提取最重要的顶层目录。
DEFAULT_KEY_DIR_NAMES = {
    "src",
    "tests",
    "docs",
    "config",
    "scripts",
}


def scan_files(repo_path: str) -> tuple[list[str], list[str]]:
    """
    输入：
        repo_path：本地项目路径（字符串）。
    输出：
        tuple[list[str], list[str]]
        第一个列表是被纳入分析的文件绝对路径；
        第二个列表是被忽略的路径绝对路径（目录或文件）。
    作用：
        扫描项目文件系统，应用忽略规则，得到后续统计与目录树构建所需的基础数据。
    设计原因：
        将“遍历 + 忽略规则应用”集中在一个函数中，后续目录树、统计、入口识别都可复用这个结果。
    """
    root = Path(repo_path).resolve()# resolve() 将路径转换为绝对路径
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"路径不是目录: {root}")

    kept_files: list[str] = []
    ignored_paths: list[str] = []

    for current_root, dir_names, file_names in root.walk(top_down=True):# walk() 遍历目录树，top_down=True 允许我们修改 dir_names 来控制遍历行为。
        # 先过滤目录，避免进入被忽略目录内部。
        next_dirs: list[str] = []
        for dir_name in dir_names:
            if should_ignore_dir(dir_name):
                dir_path = current_root / dir_name
                ignored_paths.append(str(dir_path))
                continue
            next_dirs.append(dir_name)
        dir_names[:] = next_dirs# 修改 dir_names 内容，不修改引用

        # 处理当前目录下的文件。
        for file_name in file_names:
            file_path = current_root / file_name
            if should_ignore_file(file_path):
                ignored_paths.append(str(file_path))
                continue
            kept_files.append(str(file_path))

    kept_files.sort()
    ignored_paths.sort()
    return kept_files, ignored_paths


def count_file_types(files: list[str]) -> dict[str, int]:
    """
    输入：
        files：扫描后保留的文件绝对路径列表。
    输出：
        dict[str, int]，键为文件后缀（如 ".py"），值为该类型文件数量。
    作用：
        统计项目文件类型分布，用于判断项目技术栈和文件构成。
    设计原因：
        文件类型统计是 V1 的核心输出之一，单独封装便于复用与测试。
    """
    type_counter: dict[str, int] = {}

    for file_path in files:
        suffix = Path(file_path).suffix.lower()
        if not suffix:
            suffix = "[无后缀]"
        type_counter[suffix] = type_counter.get(suffix, 0) + 1

    return dict(sorted(type_counter.items(), key=lambda item: item[0]))# sorted返回一个新的列表，dict() 将其转换回字典，按后缀字母顺序排序。


def find_entry_candidates(files: list[str]) -> list[str]:
    """
    输入：
        files：扫描后保留的文件绝对路径列表。
    输出：
        list[str]，可能作为项目入口的文件路径列表（按优先级排序）。
    作用：
        基于规则给出入口候选，帮助快速定位项目启动点。
    设计原因：
        V1 先用确定性规则实现入口识别，保证结果可解释、可测试。
    """
    src_candidates: list[str] = []
    other_candidates: list[str] = []

    for file_path in files:
        path_obj = Path(file_path)
        if path_obj.name not in DEFAULT_ENTRY_CANDIDATE_NAMES:
            continue

        parts_lower = {part.lower() for part in path_obj.parts}# 将路径的每个部分转换为小写，存储在一个集合中
        if "src" in parts_lower:
            src_candidates.append(str(path_obj))
        else:
            other_candidates.append(str(path_obj))

    src_candidates.sort()
    other_candidates.sort()
    return src_candidates + other_candidates


def summarize_key_dirs(files: list[str], repo_path: str) -> list[str]:
    """
    输入：
        files：扫描后保留的文件绝对路径列表。
        repo_path：项目根目录路径。
    输出：
        list[str]，识别出的主要顶层目录名（按字母顺序）。
    作用：
        从文件分布中提取项目最关键的目录区域，帮助快速理解项目结构。
    设计原因：
        V1 先提供简单稳定的目录摘要，避免引入复杂语义分析。
    """
    root = Path(repo_path).resolve()
    top_level_dir_names: set[str] = set()

    for file_path in files:
        path_obj = Path(file_path).resolve()
        try:
            relative_path = path_obj.relative_to(root)# relative_to() 计算 path_obj 相对于 root 的相对路径，如果 path_obj 不在 root 的子目录中，则会抛出 ValueError 异常。
        except ValueError:
            # 不在当前仓库根目录下的路径直接跳过，避免污染结果。
            continue

        parts = relative_path.parts
        if len(parts) < 2:
            # 根目录文件（如 README.md）没有“顶层子目录”，不计入 key dirs。
            continue

        # 取相对路径第一段，才是仓库意义上的“顶层目录”。
        top_dir = parts[0]
        if top_dir.lower() in DEFAULT_KEY_DIR_NAMES:
            top_level_dir_names.add(top_dir)

    return sorted(top_level_dir_names)


def build_file_tree(files: list[str], repo_path: str) -> str:
    """
    输入：
        files：扫描后保留的文件绝对路径列表。
        repo_path：项目根目录路径。
    输出：
        str，文本目录树。
    作用：
        将文件路径集合转换为可读的层级结构，便于快速查看项目全貌。
    设计原因：
        V1 需要稳定、可直接展示的目录树输出，作为项目结构扫描结果核心部分。
    """
    root = Path(repo_path).resolve()
    root_label = root.name
    tree_lines: list[str] = [root_label + "/"]

    children_map: dict[tuple[str, ...], set[str]] = {} # 键是父节点路径（tuple），值是该父节点下的直接子节点名称集合。
    terminal_files: set[tuple[str, ...]] = set() # 判断是否是文件，是否到终点

    for file_path in files:
        path_obj = Path(file_path).resolve()
        try:
            relative_path = path_obj.relative_to(root)
        except ValueError:
            continue

        parts = relative_path.parts
        if not parts:
            continue

        # 建立每一层目录到其直接子节点的映射。
        for depth in range(len(parts)):
            parent = parts[:depth]
            child = parts[depth] 
            children_map.setdefault(parent, set()).add(child)# setdefault() 方法用于获取指定键的值，如果键不存在，则将键与默认值（这里是一个空集合）关联，并返回该默认值。这样可以确保每个父节点都有一个集合来存储其子节点。

        terminal_files.add(parts)

    def render(node_parts: tuple[str, ...], prefix: str) -> None:
        children = sorted(children_map.get(node_parts, []))# 获取当前节点的子节点列表，并按字母顺序排序。node_parts 是一个元组，表示当前节点的路径部分。children_map.get(node_parts, []) 会返回该节点的子节点集合，如果没有子节点，则返回一个空列表。
        for index, child in enumerate(children):
            is_last = (index == len(children) - 1)
            branch = "└── " if is_last else "├── "
            child_parts = node_parts + (child,)
            is_file = child_parts in terminal_files
            suffix = "" if is_file else "/" # 目录后面加斜杠，文件不加。
            tree_lines.append(f"{prefix}{branch}{child}{suffix}")

            if not is_file:
                next_prefix = prefix + ("    " if is_last else "│   ")
                render(child_parts, next_prefix)

    render((), "")
    return "\n".join(tree_lines)


def run_v1_scan(repo_path: str) -> dict[str, object]:
    """
    输入：
        repo_path：项目根目录路径。
    输出：
        dict[str, object]，包含 V1 全量结构化扫描结果。
    作用：
        聚合 V1 各个子能力，提供单一调用入口给 CLI 或其他模块。
    设计原因：
        将流程编排和具体实现解耦，避免上层重复拼装扫描步骤。
    """
    kept_files, ignored_paths = scan_files(repo_path)
    return {
        "repo_path": str(Path(repo_path).resolve()),
        "tree": build_file_tree(kept_files, repo_path),
        "file_count": len(kept_files),
        "file_types": count_file_types(kept_files),
        "key_dirs": summarize_key_dirs(kept_files, repo_path),
        "entry_candidates": find_entry_candidates(kept_files),
        "ignored_paths": ignored_paths,
    }


def generate_v1_report(scan_result: dict[str, object]) -> str:
    """
    输入：
        scan_result：run_v1_scan 返回的结构化结果字典。
    输出：
        str，Markdown 文本报告。
    作用：
        将结构化扫描结果渲染为人可读报告，便于直接查看与分享。
    设计原因：
        展示层与数据层分离，后续可平滑扩展为 JSON、HTML 等输出格式。
    """
    repo_path = str(scan_result["repo_path"])
    tree = str(scan_result["tree"])
    file_count = int(scan_result["file_count"])
    file_types = scan_result["file_types"]
    key_dirs = scan_result["key_dirs"]
    entry_candidates = scan_result["entry_candidates"]
    ignored_paths = scan_result["ignored_paths"]

    lines: list[str] = []
    lines.append(f"# V1 项目结构扫描报告")
    lines.append("")
    lines.append(f"- 项目路径: `{repo_path}`")
    lines.append(f"- 纳入分析文件数: `{file_count}`")
    lines.append(f"- 忽略路径数: `{len(ignored_paths)}`")
    lines.append("")

    lines.append("## 目录树")
    lines.append("```text")
    lines.append(tree)
    lines.append("```")
    lines.append("")

    lines.append("## 文件类型统计")
    if isinstance(file_types, dict) and file_types:
        for suffix, count in file_types.items():
            lines.append(f"- `{suffix}`: `{count}`")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 主要目录")
    if isinstance(key_dirs, list) and key_dirs:
        for item in key_dirs:
            lines.append(f"- `{item}`")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 入口候选文件")
    if isinstance(entry_candidates, list) and entry_candidates:
        for item in entry_candidates:
            lines.append(f"- `{item}`")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 忽略路径")
    if isinstance(ignored_paths, list) and ignored_paths:
        for item in ignored_paths:
            lines.append(f"- `{item}`")
    else:
        lines.append("- 无")

    return "\n".join(lines)
