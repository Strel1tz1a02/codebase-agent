from __future__ import annotations

from pathlib import Path

# V1 默认忽略目录：这些目录通常是依赖、缓存或构建产物，不属于业务源码。
DEFAULT_IGNORED_DIRS = {
    ".git",
    ".pytest_cache",
    ".vscode",
    ".idea",
    ".codebase_agent",
    "node_modules",
    "__pycache__",
    ".venv",
    "dist",
    "build",
}

# V1 默认忽略文件：与源码分析无关的系统噪声文件。
DEFAULT_IGNORED_FILES = {
    ".DS_Store",  # macOS Finder 自动生成的目录信息文件。
}

# V1 默认忽略后缀：常见临时/生成文件后缀。
DEFAULT_IGNORED_SUFFIXES = {
    ".pyc",  # Python 编译后的字节码文件。
    ".log",  # 日志文件，通常用于运行记录，不是源码。
}


def should_ignore_dir(dir_name: str) -> bool:
    """
    输入：
        dir_name：当前目录名（不是完整路径），例如 ".git"。
    输出：
        bool，True 表示应忽略该目录，False 表示保留。
    作用：
        在遍历阶段快速过滤掉体积大或无关目录。
    设计原因：
        目录过滤会被高频调用，单独封装便于维护和后续扩展规则。
    """
    return dir_name in DEFAULT_IGNORED_DIRS


def should_ignore_file(file_path: str | Path) -> bool:
    """
    输入：
        file_path：文件路径（str 或 Path）。
    输出：
        bool，True 表示应忽略该文件，False 表示保留。
    作用：
        过滤噪声文件和自动生成文件类型。
    设计原因：
        文件规则与目录规则语义不同，拆分后逻辑更清晰、测试更聚焦。
    """
    path = Path(file_path)
    if path.name in DEFAULT_IGNORED_FILES:
        return True
    if path.suffix.lower() in DEFAULT_IGNORED_SUFFIXES:
        return True
    return False

