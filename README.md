# codebase-agent

面向代码仓库理解的 Agent 实验项目。

当前实现状态：

1. V1：项目结构扫描器
2. V1.5：基于关键文件上下文的 LLM 项目问答（不使用 RAG）

## 1. 环境要求

1. Python 3.11（推荐）
2. 可用的网络环境（用于调用 LLM API）

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

> `requirements.txt` 当前最小依赖为 `openai>=1.0.0`。

## 3. V1：项目结构扫描

```bash
python src/main.py --repo E:\projects\test_project_v1
```

输出包含：

1. 项目目录树
2. 文件总数
3. 文件类型统计
4. 主要目录
5. 入口候选文件
6. 忽略路径

## 4. V1.5：项目问答

V1.5 使用命令行参数注入 LLM 配置（不依赖环境变量）：

必填参数：

1. `--provider`
2. `--model`
3. `--api-key`

可选参数：

1. `--base-url`

示例（阿里云兼容模式）：

```bash
python src/main.py --repo E:\projects\codebase-agent --ask "这个项目入口在哪里？" --provider aliyun --model qwen-plus --api-key <你的key> --base-url https://dashscope.aliyuncs.com/compatible-mode/v1
```

输出包含：

1. `Prompt`
2. `回答`
3. `使用的上下文文件`

## 5. 已注册 Provider 与模型

当前在 `src/llm/client.py` 中维护注册表（`PROVIDER_MODEL_REGISTRY`），调用时要求模型命中当前 provider 的注册集合。

已注册 provider：

1. `openai`
2. `aliyun`
3. `deepseek`
4. `siliconflow`
5. `zhipu`
6. `baidu`

## 6. 测试

运行全量测试：

```bash
python -m unittest discover -s tests
```
