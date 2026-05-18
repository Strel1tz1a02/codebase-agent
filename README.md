# codebase-agent

一个面向代码仓库理解的 Agent 项目。  
当前已完成 V1：项目结构扫描器。

## V1 功能

输入本地项目路径，输出：

1. 项目目录树
2. 文件总数
3. 文件类型统计
4. 主要目录
5. 入口候选文件
6. 忽略路径列表

## 项目结构（当前）

```text
codebase-agent/
├── Docs/
├── src/
│   ├── main.py
│   ├── tools/
│   │   └── file_tools.py
│   └── utils/
│       └── ignore.py
└── tests/
    └── test_v1_file_tools.py
```

## 运行方式

```bash
python src/main.py --repo E:\projects\test_project_v1
```

## 输出说明

- `tree`：项目目录树（文本）
- `file_count`：纳入分析的文件数量
- `file_types`：按后缀统计的文件类型数量
- `key_dirs`：识别出的主要目录（如 `src/tests/docs`）
- `entry_candidates`：入口候选文件路径
- `ignored_paths`：被忽略的目录/文件路径

## 运行测试

```bash
python -m unittest tests/test_v1_file_tools.py -v
```

## 当前限制（V1）

- 仅支持本地路径扫描
- 不解析 `.gitignore` 语义（使用内置忽略规则）
- 不做 RAG / 问答 / LLM 分析

## 下一步（V2 方向）

1. 代码切分与向量索引
2. 基于检索的代码问答（RAG）
3. 结合 Tool Calling 自动读取与定位代码
