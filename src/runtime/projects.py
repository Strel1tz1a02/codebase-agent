from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class Project:
    """
    输入：
        project_id：项目唯一标识。
        name：用户可读的项目名称。
        repo_path：项目绑定的本地仓库路径。
        index_status：RAG 索引状态。
    输出：
        Project 数据对象。
    作用：
        表示一个被 codebase-agent 注册和分析的代码仓库。
    为什么需要这个类：
        成熟 Runtime 不能只围绕一次 ask 工作；需要先有 project，后续 session、run 和 index 都绑定到它。
    """

    project_id: str
    name: str
    repo_path: str
    index_status: Literal["not_indexed", "indexing", "indexed", "failed"] = "not_indexed"

