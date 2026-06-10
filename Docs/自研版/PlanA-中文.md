# Codebase Agent Platform 重构规划

## 背景

当前项目已经完成了从本地代码扫描器到基于 LangGraph 的 Agent 的核心学习路径：

1. V1 项目结构扫描。
2. V2 代码 RAG 检索。
3. V3 Tool Calling Agent 循环。
4. V4 基于 LangGraph 的工作流和测试。

下一阶段不应改变项目主题，而应将现有代码库升级为一个适合写入简历的工程化项目，同时体现 LLM 应用能力和后端 Agent 平台能力。

## 项目定位

项目将重新定位为：

```text
Codebase Agent Platform：一个基于 LangGraph 的代码库理解与 Agent Runtime 平台。
```

该项目不只是一个代码问答工具，而是一个用于索引代码仓库、检索代码上下文、选择工具、管理多轮会话、暴露 API、评测 Agent 行为的 Agent 平台。

## 目标能力覆盖

### 核心路线

项目将结合三个方向：

1. 以产品功能体现 LLM 应用能力。
2. 以 Agent Runtime 和后端平台能力作为系统骨架。
3. 以轻量级 RAG 和搜索优化作为可量化的技术深度。

### 能力映射

| 能力领域 | 项目证据 |
| --- | --- |
| Python 后端 | FastAPI 服务、服务层、测试、CLI 兼容 |
| API 开发 | 仓库索引、会话创建、问答接口、工具列表接口 |
| 异步与并发 | 异步 FastAPI handler、面向后台任务的 runtime 边界 |
| LLM 应用 | Prompt 模板、工具调用、多轮上下文、答案生成 |
| RAG | 代码加载器、切分器、Embedding、索引缓存、检索、引用 |
| 搜索优化 | 混合评分、简单重排、基于元数据的检索 |
| Agent 核心 | LangGraph 工作流、规划循环、工具选择、Memory、最大步数控制 |
| 框架 | 使用 LangGraph 作为主要 Agent 编排框架 |
| 工具体系 | MCP 风格工具注册表、schema、权限、参数校验 |
| Agent Runtime | Session 状态、任务状态、Trace、重试、失败处理 |
| 评测 | Agent 成功率、召回命中率、工具调用准确率、幻觉检查 |
| 工程化 | Docker、结构化日志、README、演示脚本、架构文档 |

SFT、RLHF、DPO、PPO、Reward Model、LoRA 等训练主题有意不纳入本项目范围。这些属于模型优化方向，而本仓库定位为 Agent 应用与 Runtime 工程项目。

## 架构设计

升级后的系统采用六层架构。

### 1. RAG 知识层

负责将本地代码仓库转换为可搜索的代码知识。

职责：

1. 在遵守 ignore 规则的前提下加载源码文件。
2. 将代码切分为 chunk。
3. 附加路径、语言、起始行、结束行、符号名等元数据。
4. 构建并缓存 Embedding。
5. 针对查询召回 top-k 代码片段。
6. 使用轻量级混合分数对召回结果进行重排。
7. 为下游答案生成返回引用信息。

预期简历证据：

```text
实现了代码 RAG，支持 chunk 元数据、向量检索、混合重排和基于引用的答案生成。
```

### 2. Tool Calling 层

负责向 Agent 暴露代码仓库操作能力。

初始工具：

1. `repo_summary`：总结仓库结构。
2. `read_file`：在仓库内有边界地读取文件。
3. `search_code`：在源码、测试、文档或全部文件中进行关键词搜索。
4. `retrieve_code`：基于索引 chunk 进行语义 RAG 检索。
5. `generate_report`：生成架构分析、阅读路线和面试笔记。

工具协议：

1. `name`
2. `description`
3. `input_schema`
4. `permission`
5. `handler`

权限类型：

1. `read_only`
2. `retrieval`
3. `report`

第一个平台版本保持只读。除非后续显式加入更强的沙箱能力，否则写操作不纳入范围。

预期简历证据：

```text
设计了 MCP 风格工具注册表，支持 schema 校验、权限边界和统一工具执行结果。
```

### 3. Agent Runtime 层

负责可靠地运行 Agent 会话。

Runtime 概念：

1. `Session`：围绕一个仓库的一次多轮对话。
2. `AgentState`：当前推理步骤的 LangGraph 状态。
3. `ToolCall`：一次工具决策和执行结果。
4. `Trace`：用于调试和评测的结构化运行历史。
5. `TaskStatus`：`running`、`completed`、`failed` 或 `stopped`。

Runtime 行为：

1. 维护多轮历史。
2. 在追问中保留短期记忆。
3. 限制最大工具调用次数。
4. 对可恢复的工具失败进行重试。
5. 当 Agent 无法继续时给出清晰停止原因。
6. 返回 trace 数据用于可观测性和评测。

预期简历证据：

```text
构建了 Agent Runtime，支持会话管理、多轮记忆、任务状态跟踪、失败重试和结构化 Trace。
```

### 4. API 服务层

负责将项目封装为可用的后端服务。

计划中的 FastAPI 接口：

1. `POST /repositories/index`
   - 构建或刷新仓库索引。
2. `POST /sessions`
   - 创建绑定到指定仓库路径的会话。
3. `POST /sessions/{session_id}/ask`
   - 在指定会话中提问。
4. `GET /sessions/{session_id}`
   - 查看会话状态、历史和最新答案。
5. `GET /tools`
   - 列出已注册工具和权限。
6. `GET /health`
   - 健康检查。

现有 CLI 继续保留，并尽可能调用相同的 service/runtime 函数。

预期简历证据：

```text
通过 FastAPI API 暴露 Agent Runtime，同时保留 CLI 兼容性。
```

### 5. Evaluation 评测层

负责量化 Agent 是否有效。

评测数据格式：

```json
{
  "id": "entrypoint_location",
  "question": "Where is the project entry point?",
  "expected_files": ["src/main.py"],
  "expected_keywords": ["main", "argparse"],
  "expected_tools": ["repo_summary", "search_code"],
  "requires_citation": true
}
```

指标：

1. Retrieval hit rate。
2. Tool-call accuracy。
3. Citation coverage。
4. Agent success rate。
5. Hallucination flag rate。

幻觉控制先从确定性检查开始：

1. 如果答案提到不存在的文件路径，则标记。
2. 如果答案需要证据但没有引用，则标记。
3. 如果预期文件没有被召回或引用，则将该用例标记为部分失败。

预期简历证据：

```text
构建了自动化评测集，用于衡量召回命中率、工具调用准确率、引用覆盖率、Agent 成功率和幻觉风险。
```

### 6. 部署与展示层

负责让项目易于运行和展示。

交付物：

1. Dockerfile。
2. Docker Compose 文件。
3. 结构化日志。
4. 架构图。
5. README 重写。
6. Demo 脚本。
7. 面试 Q&A 笔记。
8. 简历 bullet 示例。

预期简历证据：

```text
使用 Docker 容器化 Agent 服务，并沉淀架构、演示流程、评测结果和工程取舍文档。
```

## 版本路线图

### V5：RAG 工具集成

目标：

将当前 RAG 模块接入 Agent 工具层。

范围：

1. 增加 `retrieve_code` 作为 Agent 工具。
2. 返回路径、行号范围、内容和分数。
3. 让 Agent 在 `search_code` 和 `retrieve_code` 之间做选择。
4. 使用检索代码时，要求最终答案包含引用。
5. 增加检索工具执行和答案上下文流转测试。

简历能力：

RAG、Tool Calling、基于引用的幻觉控制。

### V6：Agent Runtime 与 Session Memory

目标：

将 Agent 从一次性 runner 升级为 runtime。

范围：

1. 增加 session model。
2. 增加内存 session store。
3. 在多轮对话中保留 conversation history。
4. 增加结构化 trace 记录。
5. 增加清晰的 stop reason。

简历能力：

Agent Runtime、会话管理、Memory、失败处理、状态管理。

### V7：FastAPI 服务

目标：

将 runtime 暴露为后端服务。

范围：

1. 增加 FastAPI 依赖。
2. 增加 API schema。
3. 增加仓库索引接口。
4. 增加 session 接口。
5. 增加 ask 接口。
6. 增加 tool list 和 health 接口。
7. 增加 API 测试。

简历能力：

Python 后端、API 开发、服务边界、后端测试。

### V8：MCP 风格工具协议

目标：

让工具注册显式化、可扩展化。

范围：

1. 定义 `ToolSpec`。
2. 定义 input schema validation。
3. 定义 permission categories。
4. 将现有工具重构进 registry。
5. 在执行前增加 permission check。
6. 增加非法参数、未知工具、被拒绝工具的测试。
7. 增加工具执行失败的 retry policy。

简历能力：

MCP/工具生态、插件式扩展、权限控制、工具沙箱边界。

### V9：RAG 与 Agent 评测

目标：

增加可量化的质量评测。

范围：

1. 增加 `eval_cases.jsonl`。
2. 增加 evaluation runner。
3. 衡量 retrieval hit rate。
4. 衡量 tool-call accuracy。
5. 衡量 citation coverage。
6. 增加确定性 hallucination checks。
7. 生成 JSON 和 Markdown 评测报告。

简历能力：

Agent 评测、RAG 评测、自动化测试集、幻觉控制。

### V10：工程化打包

目标：

让项目适合 GitHub、简历和面试展示。

范围：

1. 增加 Dockerfile。
2. 增加 Docker Compose。
3. 增加结构化日志。
4. 重写 README。
5. 增加架构图。
6. 增加 demo commands。
7. 增加简历 bullet。
8. 增加面试 Q&A。

简历能力：

Docker、部署、基础可观测性、文档、项目展示。

## 非目标

下一阶段实现周期中不计划包含以下内容：

1. 模型训练或微调。
2. SFT、RLHF、DPO、PPO、Reward Model、LoRA 或 QLoRA。
3. 多 Agent 角色协作。
4. 真实 Kubernetes 部署。
5. 对被分析仓库的写操作。
6. 浏览器或 GUI 自动化。
7. 多模态输入。

这些主题可以作为未来方向提及，但不应分散当前核心 Agent 平台的建设重点。

## 验收标准

当满足以下条件时，该重构项目可视为简历就绪：

1. 用户可以索引一个仓库。
2. 用户可以创建一个 session 并进行追问。
3. Agent 可以通过 LangGraph 选择工具。
4. Agent 可以同时使用关键词搜索和 RAG 检索。
5. 基于仓库内容的答案包含引用。
6. 工具执行经过校验并进行权限检查。
7. 可以查看 session history 和 trace。
8. 评测可以通过一条命令运行并产出指标。
9. 服务可以通过 Docker 运行。
10. README 解释架构、用法、评测、限制和简历价值。

## 推荐简历描述

```text
构建 Codebase Agent Platform，一个基于 LangGraph 的代码库理解 Agent Runtime。系统支持仓库索引、RAG 检索、Tool Calling、多轮 Session Memory、MCP 风格工具注册、权限检查、结构化 Trace 和 FastAPI 服务接口。构建自动化评测集，衡量召回命中率、工具调用准确率、引用覆盖率、Agent 成功率和幻觉风险，并使用 Docker 对服务进行容器化。
```

## 实施策略

每个版本必须包含：

1. 聚焦的实现改动。
2. 单元测试或集成测试。
3. 当用户可见行为发生变化时更新文档。
4. 可运行的验证命令。

实现顺序为 V5 到 V10。在当前版本完成测试和文档之前，不应启动后续版本。
