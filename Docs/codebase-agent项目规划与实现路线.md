# 怎么完成项目

每写一个模块，都必须说明：

1. 这个模块解决什么问题

2. 为什么这样设计

3. 和 Agent 项目有什么关系

4. 哪些经典项目里有类似实现

5. 我应该去看经典项目的哪个部分

# 项目名称

建议用：

```
codebase-agent
```

项目中文名：

```
代码仓库分析 Agent
```

简历名：

```
基于 LangGraph 的代码仓库分析 Agent
```

---

# 项目结构

codebase-agent/
├── [README.md](http://readme.md/)
├── requirements.txt
├── .env.example
├── .gitignore
├── src/
│   ├── [main.py](http://main.py/)
│   ├── [config.py](http://config.py/)
│   ├── [state.py](http://state.py/)
│   ├── [graph.py](http://graph.py/)
│   ├── tools/
│   │   ├── **init**.py
│   │   ├── file_tools.py
│   │   ├── search_tools.py
│   │   └── summary_tools.py
│   ├── rag/
│   │   ├── **init**.py
│   │   ├── [loader.py](http://loader.py/)
│   │   ├── [splitter.py](http://splitter.py/)
│   │   ├── [embeddings.py](http://embeddings.py/)
│   │   └── [retriever.py](http://retriever.py/)
│   ├── prompts/
│   │   ├── **init**.py
│   │   ├── system_prompt.py
│   │   └── [templates.py](http://templates.py/)
│   ├── nodes/
│   │   ├── **init**.py
│   │   ├── analyze_question.py
│   │   ├── execute_tool.py
│   │   └── generate_answer.py
│   └── utils/
│       ├── **init**.py
│       ├── [logger.py](http://logger.py/)
│       └── [ignore.py](http://ignore.py/)
├── examples/
│   └── [demo.md](http://demo.md/)
├── docs/
│   ├── [architecture.md](http://architecture.md/)
│   ├── [usage.md](http://usage.md/)
│   └── [interview.md](http://interview.md/)
└── tests/
└── test_file_tools.py

# 项目最终功能

最终希望实现：

```
1. 输入本地项目路径
2. 自动扫描项目目录
3. 识别核心文件
4. 建立代码索引
5. 支持自然语言问答
6. 自动调用工具读取代码
7. 输出带文件路径的答案
8. 生成项目阅读路线
9. 生成项目结构总结
10. 生成面试讲解稿
```

---

# 项目版本规划

---

## V1：项目结构扫描器

### 目标

先不做复杂 Agent，只做一个能分析项目结构的小工具。

---

### 你要做什么

实现：

```
输入：本地项目路径
输出：
1. 项目目录树
2. 文件数量统计
3. 文件类型统计
4. 主要目录说明
5. 可能的入口文件
```

---

### 需要学什么

```
pathlib
os.walk
文件过滤
ignore 规则
Markdown 输出
LLM 总结
```

---

### 需要写哪些文件

```
src/tools/file_tools.py
src/utils/ignore.py
src/main.py
```

---

### 功能示例

用户输入：

```
python src/main.py --repo ./test_project
```

输出：

```
项目结构：
- src/
- tests/
- README.md
- requirements.txt

分析结果：
这是一个 Python 项目，核心代码位于 src 目录，测试代码位于 tests 目录。
```

---

### 完成标准

```
能扫描一个本地项目
能输出目录树
能忽略 .git / __pycache__ / node_modules
能生成简单项目结构说明
```

---

## V2：代码问答 RAG

### 目标

让用户可以针对代码提问。

---

### 你要做什么

实现：

```
1. 读取项目代码文件
2. 对代码进行切分
3. 建立向量索引
4. 用户提问
5. 检索相关代码片段
6. 调用模型回答
7. 返回引用文件路径
```

---

### 需要学什么

```
chunking
embedding
FAISS 或 Chroma
retriever
metadata
top-k
prompt template
```

---

### 需要写哪些文件

```
src/rag/loader.py
src/rag/splitter.py
src/rag/embeddings.py
src/rag/retriever.py
src/prompts/templates.py
```

---

### 功能示例

用户问：

```
这个项目的入口在哪里？
```

系统回答：

```
项目入口可能在 src/main.py。

依据：
- src/main.py 中包含 main() 函数
- README.md 中运行命令指向 src/main.py
```

---

### 完成标准

```
能基于代码回答问题
回答中包含文件路径
不是凭空回答
检索结果基本相关
```

---

## V3：Tool Calling Agent

### 目标

让模型不只是被动问答，而是可以选择工具。

---

### 你要做什么

实现工具：

```
list_files(path)
read_file(path)
search_code(keyword)
retrieve_code(query)
summarize_file(path)
```

让模型能根据问题选择工具。

---

### 需要学什么

```
tool schema
function calling
参数校验
工具执行
工具结果回传
错误处理
```

---

### 示例流程

用户问：

```
登录逻辑在哪？
```

Agent 执行：

```
1. 调用 search_code("login auth token")
2. 找到 auth.py
3. 调用 read_file("src/auth.py")
4. 总结登录逻辑
5. 返回答案
```

---

### 完成标准

```
模型能自动选择工具
工具调用结果能进入下一轮回答
工具失败时有错误提示
```

---

## V4：LangGraph Agent 化

### 目标

用 LangGraph 管理完整 Agent 流程。

---

### 你要做什么

把流程改成图：

```
start
→ analyze_question
→ decide_action
→ execute_tool
→ should_continue
→ generate_answer
→ end
```

---

### 需要学什么

```
StateGraph
TypedDict state
node
edge
conditional edge
tool node
循环控制
checkpoint
```

---

### 需要写哪些文件

```
src/state.py
src/graph.py
src/nodes/analyze_question.py
src/nodes/execute_tool.py
src/nodes/generate_answer.py
```

---

### State 设计

```
classAgentState(TypedDict):
repo_path:str
user_query:str
messages:list
file_tree:str
retrieved_chunks:list
selected_files:list
tool_results:list
step_count:int
final_answer:str
```

---

### 完成标准

```
Agent 流程由 LangGraph 编排
每一步 state 都能传递
支持多步工具调用
能限制最大执行步数
```

---

## V5：项目阅读助手

### 目标

让项目更适合简历和面试展示。

---

### 你要做什么

增加功能：

```
1. 生成项目阅读路线
2. 生成模块说明
3. 生成 Notion 风格笔记
4. 生成项目架构说明
5. 生成面试讲解稿
6. 分析项目亮点
7. 分析项目可优化点
```

---

### 示例输出

用户输入：

```
帮我生成这个项目的阅读路线
```

Agent 输出：

```
1. 先看 README.md
2. 再看 src/main.py
3. 然后看 src/graph.py
4. 接着看 src/tools/
5. 最后看 src/rag/
```

---

### 完成标准

```
不仅能回答问题，还能主动组织项目学习路线
输出内容适合复制到 Notion
```

---

## V6：项目包装和展示

### 目标

让项目能写进简历。

---

### 你要做什么

补齐：

```
README.md
项目架构图
运行截图
使用示例
演示视频脚本
技术难点说明
项目优化方向
简历描述
面试问答
```

---

### README 必须包含

```
1. 项目背景
2. 项目功能
3. 技术栈
4. 系统架构
5. 快速开始
6. 使用示例
7. 项目亮点
8. 后续优化
```

# 第 1 周：Python 工程 + LLM API

## 本周目标

完成一个最小 LLM 应用。

---

## 学什么

```
Python 项目结构
.env
API 调用
messages
prompt template
structured output
日志
异常处理
```

---

## 做什么

实现：

```
mini_chat.py
```

功能：

```
1. 输入用户问题
2. 加载 system prompt
3. 调用 LLM
4. 输出回答
5. 保存 messages
```

---

## 本周产出

```
一个可以运行的命令行 LLM 问答工具
```

---

# 第 2 周：项目结构扫描器 V1

## 本周目标

完成代码仓库分析 Agent 的基础版本。

---

## 学什么

```
pathlib
目录遍历
文件过滤
ignore 规则
Markdown 输出
项目结构总结
```

---

## 做什么

实现：

```
list_files(path)
build_file_tree(path)
detect_project_type(path)
summarize_structure(path)
```

---

## 本周产出

```
输入本地项目路径
输出目录树和项目结构总结
```

---

# 第 3 周：RAG V2

## 本周目标

实现基于代码的问答。

---

## 学什么

```
chunking
embedding
vector store
retriever
metadata
prompt 拼接
引用来源
```

---

## 做什么

实现：

```
load_code_files(repo_path)
split_code_files(files)
build_vector_index(chunks)
retrieve_code(query)
answer_with_context(query,chunks)
```

---

## 本周产出

```
用户可以问代码问题，系统能基于代码回答
```

---

# 第 4 周：Tool Calling V3

## 本周目标

让模型可以调用工具。

---

## 学什么

```
tool schema
function calling
参数校验
工具执行
工具结果回传
错误处理
```

---

## 做什么

实现工具：

```
list_files()
read_file()
search_code()
retrieve_code()
summarize_file()
```

并让模型根据问题自动调用工具。

---

## 本周产出

```
一个可以自动选择工具的代码分析 Agent
```

---

# 第 5 周：LangGraph V4

## 本周目标

用 LangGraph 重构 Agent 流程。

---

## 学什么

```
StateGraph
node
edge
conditional edge
state update
graph.invoke
循环控制
```

---

## 做什么

实现图流程：

```
analyze_question
→ decide_action
→ execute_tool
→ should_continue
→ generate_answer
```

---

## 本周产出

```
LangGraph 版本的代码仓库分析 Agent
```

---

# 第 6 周：增强功能 V5

## 本周目标

让项目更像真正的 Agent。

---

## 学什么

```
memory
checkpoint
多轮追问
报告生成
Notion 格式输出
```

---

## 做什么

增加：

```
项目阅读路线生成
模块总结
项目报告
面试讲解稿
多轮追问
```

---

## 本周产出

```
一个适合展示的完整 Agent 项目
```

---

# 第 7 周：项目包装

## 本周目标

让项目可以放到 GitHub 和简历上。

---

## 做什么

补齐：

```
README
架构图
使用示例
运行截图
演示视频
技术亮点
难点总结
优化方向
```

---

## 本周产出

```
GitHub 可展示版本
```

---

# 第 8 周：面试准备

## 本周目标

能讲清楚项目。

---

## 准备这些问题

```
1. 你为什么做这个项目？
2. Agent 和 ChatBot 有什么区别？
3. 为什么用 LangGraph？
4. 你的 State 怎么设计？
5. Tool Calling 怎么实现？
6. RAG 怎么做？
7. 代码怎么切分？
8. 检索不准怎么办？
9. 工具调用失败怎么办？
10. 怎么防止 Agent 无限循环？
11. 你的项目难点是什么？
12. 后续怎么优化？
```