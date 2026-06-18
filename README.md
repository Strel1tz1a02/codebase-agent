# codebase-agent

`codebase-agent` 是面向代码仓库理解的本地 Agent 实验项目。当前主路径基于：

- Server：`python -m src.server`
- API：`src.api.app:create_app`
- Runtime：`RuntimeService`
- Graph：LangGraph workflow
- RAG：先索引，再基于已存在索引召回

## 环境

项目当前使用 Conda 虚拟环境：

```powershell
conda activate codebase-agent
```

本机历史环境名也可能是 `CodeBaseAgent`，如果 `codebase-agent` 不存在，可以使用：

```powershell
conda activate CodeBaseAgent
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## Server

启动 API 服务：

```powershell
python -m src.server
```

## API

启动服务后可访问：

```powershell
curl http://127.0.0.1:8000/health
```

核心对象模型：

```text
Project -> RuntimeSession -> Run -> RunEvent
```

API 路由只接入新的 `RuntimeService`，不再维护旧 runtime 和新 runtime 两套逻辑。

## 配置说明

默认测试不会调用真实 LLM。真实模型调用需要在模型配置中提供 `api_key_env`，并在本地环境变量中写入对应 API Key。

默认向量存储是本地后端，适合开发和测试。生产级向量数据库接入属于后续扩展。

## 测试

运行全量测试：

```powershell
python -m pytest -v
```
