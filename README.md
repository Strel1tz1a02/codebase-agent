# codebase-agent

面向代码仓库理解的 Agent 实验项目。

当前实现状态：

1. V1：项目结构扫描器
2. V1.5：基于关键文件上下文的 LLM 项目问答
3. V2：代码切块与 RAG 检索
4. V3：最小 Agent 循环，支持 LLM 决策、工具执行和 history 记录

## 1. 环境要求

1. Python 3.11（推荐）
2. 可用的网络环境（用于调用 LLM API）

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 3. 本地配置

项目使用本地配置文件减少 CLI 参数。提交仓库的是配置模板，不提交真实配置。

模板文件：

```text
.codebase_agent/config.example.json
```

真实配置文件：

```text
.codebase_agent/config.json
```

首次使用时复制模板：

```powershell
Copy-Item .codebase_agent\config.example.json .codebase_agent\config.json
```

真实 API Key 不写入配置文件，配置文件只保存环境变量名：

```json
{
  "llm": {
    "api_key_env": "CODEBASE_AGENT_API_KEY"
  }
}
```

PowerShell 临时设置 API Key：

```powershell
$env:CODEBASE_AGENT_API_KEY="你的真实 key"
```

长期保存：

```powershell
setx CODEBASE_AGENT_API_KEY "你的真实 key"
```

`.codebase_agent/config.json` 已加入 `.gitignore`，不要提交真实配置。

## 4. 常用命令

项目结构扫描：

```bash
python src/main.py
```

日常 Agent 问答（默认读取配置里的 `ask_mode`）：

```bash
python src/main.py --ask "入口在哪"
```

临时切换为基础问答：

```bash
python src/main.py --ask "入口在哪" --ask-mode basic
```

临时切换为 RAG 检索：

```bash
python src/main.py --ask "入口在哪" --ask-mode rag
```

强制重建 RAG 索引：

```bash
python src/main.py --ask "入口在哪" --ask-mode rag --reindex
```

构建代码 chunks：

```bash
python src/main.py --build-chunks
```

临时覆盖仓库路径：

```bash
python src/main.py --repo E:\projects\other_repo --ask "入口在哪"
```

临时覆盖 LLM 配置：

```bash
python src/main.py --ask "入口在哪" --provider aliyun --model qwen-plus --base-url https://dashscope.aliyuncs.com/compatible-mode/v1
```

## 5. 配置字段说明

`.codebase_agent/config.example.json` 示例：

```json
{
  "repo": "E:\\projects\\codebase-agent",
  "ask_mode": "agent",
  "llm": {
    "provider": "aliyun",
    "model": "qwen-plus",
    "api_key_env": "CODEBASE_AGENT_API_KEY",
    "base_url": ""
  },
  "rag": {
    "top_k": 5,
    "reindex": false
  },
  "agent": {
    "max_steps": 3
  }
}
```

字段含义：

1. `repo`：默认分析的本地代码仓库路径。
2. `ask_mode`：问答模式，可选 `basic`、`rag`、`agent`。
3. `llm.provider`：LLM provider，目前支持 `aliyun`、`deepseek`。
4. `llm.model`：模型名称，需要命中 provider 的注册模型。
5. `llm.api_key_env`：保存真实 API Key 的环境变量名。
6. `llm.base_url`：可选 API 地址；为空时使用 provider 默认地址。
7. `rag.top_k`：RAG 模式返回的 chunk 数量。
8. `rag.reindex`：是否默认重建 RAG 索引。
9. `agent.max_steps`：Agent 循环最大步数。

## 6. Agent 模式当前边界

当前 Agent 模式已经跑通最小链路：

```text
AgentContext -> build_prompt -> ask_llm -> parse_llm -> run_agent_loop -> execute_tool -> history
```

当前已有真实工具：

1. `repo_summary`：查看仓库文件数、主要目录、文件类型统计和入口候选。
2. `read_file`：读取仓库内指定文件内容，并限制路径不能逃出仓库。
3. `search_code`：按关键词搜索代码文件，返回相对路径、行号和当前行文本；默认只搜索 `src/`，可通过 `scope` 搜索 `tests`、`docs` 或 `all`。

下一步可以继续增加真实代码仓库工具，例如 `retrieve_code`。

## 7. 测试

运行全量测试：

```bash
python -m unittest discover -s tests
```
