# 1. LangGraph

## 什么时候看

当你做到：

```
state 怎么设计？
节点怎么连接？
工具调用后怎么继续？
怎么控制循环？
怎么保存执行过程？
```

时看。

---

## 看什么

重点看：

```
StateGraph
node
edge
conditional edge
checkpoint
memory
tool calling
prebuilt agent
```

---

## 你要带着这些问题看

```
1. state 是怎么定义的？
2. node 输入输出是什么？
3. node 怎么更新 state？
4. conditional edge 怎么决定下一步？
5. tool result 怎么写回 state？
6. 怎么防止 Agent 无限循环？
```

---

# 2. LangChain 示例

## 什么时候看

当你做到：

```
prompt 怎么写？
RAG 怎么接？
retriever 怎么封装？
tool 怎么定义？
```

时看。

---

## 看什么

重点看：

```
prompt template
runnable
retriever
tools
structured output
RAG chain
```

---

# 3. LlamaIndex

## 什么时候看

当你做到：

```
代码切分不准
检索效果不好
文档索引不知道怎么设计
```

时看。

---

## 看什么

重点看：

```
documents
nodes
index
retriever
query engine
metadata
```

---

# 4. OpenAI Agents SDK

## 什么时候看

当你做到：

```
tool calling
tracing
guardrails
human review
```

时看。

---

## 看什么

重点看：

```
tools
handoffs
tracing
guardrails
human-in-the-loop
```