from __future__ import annotations

import hashlib
import json
from pathlib import Path

INDEX_CACHE_RELATIVE_PATH = Path(".codebase_agent") / "index.json"


def compute_repo_fingerprint(file_records: list[dict[str, object]]) -> str:
    """
    输入：
        file_records：代码文件记录列表，每项包含 relative_path 和 content。
    输出：
        str：仓库内容指纹（sha256）。
    作用：
        基于当前可分析文件内容生成稳定指纹，用于判定缓存是否可复用。
    设计原因：
        缓存有效性不能只看文件存在，必须绑定仓库内容版本。
    """
    hasher = hashlib.sha256()
    for record in file_records:
        relative_path = str(record.get("relative_path", ""))
        content = str(record.get("content", "")).replace("\r\n", "\n")
        hasher.update(relative_path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def _get_cache_path(repo_path: str) -> Path:
    """
    输入：
        repo_path：仓库根目录路径。
    输出：
        Path：索引缓存文件路径。
    作用：
        统一缓存路径规则。
    设计原因：
        让读缓存和写缓存复用同一定位逻辑，避免路径不一致问题。
    """
    return Path(repo_path).resolve() / INDEX_CACHE_RELATIVE_PATH


def save_index_cache(
    repo_path: str,
    repo_fingerprint: str,
    chunks: list[dict[str, object]],
    embedded_chunks: list[dict[str, object]],
    index_rows: list[dict[str, object]],
    config: dict[str, object],
) -> None:
    """
    输入：
        repo_path：仓库根目录路径。
        repo_fingerprint：当前仓库内容指纹。
        chunks：chunk 切分结果。
        embedded_chunks：embedding 结果。
        index_rows：索引行数据。
        config：当前检索配置参数。
    输出：
        无（写入磁盘缓存文件）。
    作用：
        把检索前的中间产物持久化，供后续直接复用。
    设计原因：
        避免每次检索都全量重建 chunk/embed/index，提升迭代效率。
    """
    cache_path = _get_cache_path(repo_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "repo_fingerprint": repo_fingerprint,
        "config": config,
        "chunks": chunks,
        "embedded_chunks": embedded_chunks,
        "index_rows": index_rows,
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_index_cache(repo_path: str) -> dict[str, object] | None:
    """
    输入：
        repo_path：仓库根目录路径。
    输出：
        dict[str, object] | None：缓存数据；不存在或读取失败时返回 None。
    作用：
        读取本地索引缓存。
    设计原因：
        缓存读取应容错，失败时回退到重建流程而不是直接报错退出。
    """
    cache_path = _get_cache_path(repo_path)
    if not cache_path.is_file():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def is_cache_valid(
    cache: dict[str, object] | None,
    repo_fingerprint: str,
    config: dict[str, object],
) -> bool:
    """
    输入：
        cache：缓存对象，可能为 None。
        repo_fingerprint：当前仓库指纹。
        config：当前检索配置参数。
    输出：
        bool：缓存是否可直接复用。
    作用：
        校验缓存完整性、仓库版本一致性和配置一致性。
    设计原因：
        避免仓库变更或配置变化后误用旧缓存导致检索结果失真。
    """
    if not isinstance(cache, dict):
        return False
    if str(cache.get("repo_fingerprint", "")) != repo_fingerprint:
        return False
    cached_config = cache.get("config")
    if not isinstance(cached_config, dict):
        return False
    for key, value in config.items():
        if cached_config.get(key) != value:
            return False
    for key in ("chunks", "embedded_chunks", "index_rows"):
        if key not in cache:
            return False
    return True
