# LangGraph and LangChain Mature Architecture Design

## Context

The project is currently a learning-oriented codebase understanding agent. It already has useful boundaries:

- `src/agent/` contains a custom decision protocol, tools, nodes, and a LangGraph wrapper.
- `src/runtime/` owns sessions and adapts runtime payloads into the graph runner.
- `src/rag/` owns custom code loading, chunking, deterministic hash embeddings, in-memory indexing, cache, and retrieval.
- `src/llm/` calls OpenAI-compatible chat completion APIs directly.
- `src/api/` exposes a small FastAPI surface for health, tools, sessions, and asks.

The next version should prioritize mature project architecture over backward compatibility. Existing CLI/API contracts may change if the new contracts are clearer and closer to production agent systems.

## Goal

Rebuild the project around LangGraph as the orchestration layer and LangChain as the standard component layer for models, tools, documents, retrievers, embeddings, and vector stores.

The result should feel like a maintainable codebase-agent service rather than a sequence of educational versions.

## Chosen Approach

Use a LangGraph-first architecture with LangChain standard components.

LangGraph will own the long-running, stateful workflow. LangChain will provide replaceable abstractions for chat models, tool schemas, documents, embeddings, retrievers, and vector stores. The current hand-written tool registry, decision JSON protocol, hash embedding implementation, and in-memory vector index should be replaced or wrapped by these standard interfaces.

This is preferred over using a high-level LangChain agent alone because codebase analysis needs explicit control over retrieval, local file access, tool safety, traceability, and future human-in-the-loop checkpoints.

## Architecture

### Proposed Package Layout

```text
src/
  api/
    app.py
    schemas.py
    routes_projects.py
    routes_sessions.py
    routes_runs.py
  cli/
    __init__.py
    main.py
  core/
    config.py
    errors.py
    paths.py
    types.py
  graph/
    __init__.py
    builder.py
    nodes.py
    routing.py
    state.py
  models/
    __init__.py
    chat.py
    embeddings.py
    providers.py
  rag/
    __init__.py
    documents.py
    indexing.py
    retrievers.py
    vectorstores.py
  runtime/
    __init__.py
    checkpoints.py
    events.py
    runs.py
    sessions.py
  tools/
    __init__.py
    codebase.py
    filesystem.py
    registry.py
```

The split is by responsibility:

- `core` contains configuration, path safety, shared types, and domain errors.
- `models` creates LangChain chat models and embeddings from project config.
- `tools` exposes LangChain-compatible tools with Pydantic argument schemas.
- `rag` turns repository files into LangChain `Document` objects and exposes retrievers backed by configurable vector stores.
- `graph` builds the LangGraph workflow and owns state transitions.
- `runtime` owns project/session/run state, run events, and checkpoint integration.
- `api` and `cli` are delivery surfaces over runtime use cases.

### Model Layer

Replace direct calls in `src/llm/client.py` with factory functions that return LangChain chat model and embedding instances.

The first implementation should support OpenAI-compatible providers already present in the project:

- Aliyun DashScope compatible endpoint.
- DeepSeek compatible endpoint.
- Custom `base_url`, `api_key_env`, `model`, and optional temperature.

The model layer should hide provider-specific construction. Graph nodes should depend on LangChain model interfaces, not on provider names.

### Tool Layer

Replace `TOOL_REGISTRY` with LangChain tools.

Initial tools:

- `repo_summary`: summarize file count, file types, key directories, and entry candidates.
- `read_file`: read a repository-relative file with path traversal protection.
- `search_code`: keyword search over allowed source scopes.
- `retrieve_code`: semantic retrieval through the configured retriever.

Every tool must have:

- A Pydantic args schema.
- Repository root validation.
- Clear output shape.
- Tests for success, validation failure, and path safety where applicable.

Tool outputs should stay structured dictionaries so graph nodes can cite paths and line ranges reliably.

### RAG Layer

Replace custom hash embeddings and global in-memory index with LangChain abstractions.

The default development backend should be local and easy to run:

- Use LangChain `Document` for code chunks.
- Use a configurable embedding model.
- Use a local VectorStore backend by default.
- Keep a `VectorStoreFactory` abstraction so Qdrant, Milvus, or pgvector can be added without changing graph logic.

The RAG layer should expose two main use cases:

- `index_project(project_id, repo_path, indexing_config)`.
- `get_retriever(project_id, retrieval_config)`.

Document metadata must include:

- `project_id`
- `repo_path`
- `relative_path`
- `start_line`
- `end_line`
- `language`
- `content_hash`

This metadata is required for citation, filtering, reindexing, and future incremental indexing.

### Graph Layer

Rebuild the workflow as an explicit LangGraph graph.

Initial graph:

```text
prepare_context
  -> classify_intent
  -> retrieve_context
  -> plan_tool_use
  -> execute_tools
  -> synthesize_answer
  -> validate_answer
  -> finish
```

Routing should be deterministic where possible:

- If the question needs code context, retrieve first.
- If retrieved context is insufficient, allow file/search tools.
- If the graph reaches configured tool or retry limits, finish with a partial answer and explicit reason.

State should use standard message objects where practical, plus project-specific fields:

- `messages`
- `project_id`
- `repo_path`
- `retrieval_hits`
- `tool_calls`
- `tool_results`
- `answer`
- `status`
- `reason`
- `events`

The current custom `decision` JSON format should be removed. Tool calling should use LangChain/LangGraph-compatible tool semantics.

### Runtime Layer

Move from a simple in-memory `SessionMemory` toward explicit project/session/run concepts.

Domain objects:

- `Project`: repository registration and index status.
- `Session`: conversation context bound to a project.
- `Run`: one user request through the graph.
- `RunEvent`: trace event emitted by graph nodes, tools, retrievers, or model calls.

The first mature version may keep these in memory, but interfaces should make persistence replaceable. A later implementation can back them with SQLite or another store.

### API Surface

Because backward compatibility is not required, redesign the API around project, session, and run resources.

Initial endpoints:

```text
GET  /health
POST /projects
GET  /projects/{project_id}
POST /projects/{project_id}/index
POST /sessions
GET  /sessions/{session_id}
POST /sessions/{session_id}/runs
GET  /sessions/{session_id}/runs/{run_id}
GET  /sessions/{session_id}/runs/{run_id}/events
GET  /tools
```

`/tools` should introspect the LangChain tool registry rather than a custom function map.

### CLI Surface

Replace mode-based educational CLI flags with workflow commands:

```bash
python -m src.cli index --repo E:\projects\codebase-agent
python -m src.cli ask --project codebase-agent "Where is the entry point?"
python -m src.cli serve
```

The CLI should call the same runtime services as the API.

## Error Handling

Errors should be structured and mapped at the delivery boundary.

Core error categories:

- `ConfigurationError`
- `ProviderError`
- `ProjectNotFoundError`
- `IndexNotReadyError`
- `PathSafetyError`
- `ToolExecutionError`
- `GraphExecutionError`

Graph nodes should record failures in run events. API handlers should convert domain errors to stable HTTP responses.

## Testing Strategy

Testing should move from version-specific behavior to architecture boundaries:

- Unit tests for config loading and provider factories.
- Unit tests for path safety and tools.
- Unit tests for document loading and metadata.
- Unit tests for vector store factory behavior using fake or in-memory embeddings.
- Graph route tests using fake chat models and fake tools.
- Runtime tests for project/session/run lifecycle.
- API contract tests using dependency-injected fake runtime services.

No tests should require real LLM API calls by default.

## Migration Strategy

The implementation should proceed in phases:

1. Add mature dependencies and configuration structures.
2. Introduce new package boundaries without deleting old modules immediately.
3. Build LangChain model and embedding factories.
4. Convert tools to LangChain-compatible tools.
5. Replace RAG internals with LangChain documents, retrievers, and vector stores.
6. Rebuild the LangGraph workflow.
7. Replace API and CLI surfaces.
8. Remove obsolete modules and tests once equivalent mature paths are covered.

This keeps the repository buildable while allowing intentional breaking changes at the API and CLI level.

## Non-Goals

The first mature architecture will not implement:

- Multi-agent collaboration.
- Background job queues.
- Persistent production database.
- Remote production vector stores by default.
- LangSmith deployment.
- Authentication or multi-tenant access control.

The design should leave extension points for these, but not build them yet.

## External References

- LangChain standardizes model, tool, and agent harness concepts and its agents are built on LangGraph.
- LangGraph is the low-level orchestration runtime for long-running, stateful agents, with support for persistence, streaming, human-in-the-loop, and observability.
- LangChain VectorStore provides a unified interface such as `add_documents`, `delete`, and `similarity_search`, making it suitable for swapping local and production vector stores.
