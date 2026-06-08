# Codebase Agent Platform Redesign

## Background

The current project has already implemented the core learning path from a local code scanner to a LangGraph-based Agent:

1. V1 project structure scanning.
2. V2 code RAG retrieval.
3. V3 tool-calling Agent loop.
4. V4 LangGraph workflow with tests.

The next stage should not change the project topic. It should upgrade the existing codebase into a resume-ready engineering project that demonstrates both LLM application skills and backend Agent platform skills.

## Project Positioning

The project will be repositioned as:

```text
Codebase Agent Platform: a LangGraph-based codebase understanding and Agent Runtime platform.
```

The project is not only a code QA tool. It is an Agent platform for indexing repositories, retrieving code context, selecting tools, managing multi-turn sessions, exposing APIs, and evaluating Agent behavior.

## Target Capability Coverage

### Core Route

The project will combine three directions:

1. LLM application capabilities as the product-facing function.
2. Agent Runtime and backend platform capabilities as the system backbone.
3. Lightweight RAG and search optimization as measurable technical depth.

### Capability Mapping

| Capability area | Planned project evidence |
| --- | --- |
| Python backend | FastAPI service, service layer, tests, CLI compatibility |
| API development | Repository indexing, session creation, ask endpoint, tool list endpoint |
| Async and concurrency | Async FastAPI handlers, background task-ready runtime boundary |
| LLM application | Prompt templates, tool calling, multi-turn context, answer generation |
| RAG | Code loader, chunker, embedding, index cache, retrieval, citation |
| Search optimization | Hybrid scoring, simple reranking, metadata-aware retrieval |
| Agent core | LangGraph workflow, planning loop, tool selection, memory, max-step control |
| Framework | LangGraph as the primary Agent orchestration framework |
| Tool ecosystem | MCP-style tool registry, schema, permissions, parameter validation |
| Agent Runtime | Session state, task status, trace, retry, failure handling |
| Evaluation | Agent success rate, retrieval hit rate, tool-call accuracy, hallucination checks |
| Engineering | Docker, structured logs, README, demo scripts, architecture docs |

Training topics such as SFT, RLHF, DPO, PPO, Reward Model, and LoRA are intentionally out of scope for this project. They are model optimization topics, while this repository is positioned as an Agent application and runtime engineering project.

## Architecture

The upgraded system will use six layers.

### 1. RAG Knowledge Layer

Responsible for turning a local repository into searchable code knowledge.

Responsibilities:

1. Load source files while respecting ignore rules.
2. Split code into chunks.
3. Attach metadata such as path, language, start line, end line, symbol name when available.
4. Build and cache embeddings.
5. Retrieve top-k chunks for a query.
6. Rerank retrieved chunks with a lightweight hybrid score.
7. Return citations for downstream answer generation.

Expected resume evidence:

```text
Implemented code RAG with chunk metadata, vector retrieval, hybrid reranking, and citation-based answer generation.
```

### 2. Tool Calling Layer

Responsible for exposing repository operations to the Agent.

Initial tools:

1. `repo_summary`: summarize repository structure.
2. `read_file`: read a bounded file inside the repository.
3. `search_code`: keyword search over source, tests, docs, or all files.
4. `retrieve_code`: semantic RAG retrieval over indexed chunks.
5. `generate_report`: generate architecture, reading route, and interview notes.

Tool protocol:

1. `name`
2. `description`
3. `input_schema`
4. `permission`
5. `handler`

Permissions:

1. `read_only`
2. `retrieval`
3. `report`

The first platform version will remain read-only. Write operations are out of scope unless explicitly added later with stronger sandboxing.

Expected resume evidence:

```text
Designed an MCP-style tool registry with schema validation, permission boundaries, and unified execution results.
```

### 3. Agent Runtime Layer

Responsible for running Agent sessions reliably.

Runtime concepts:

1. `Session`: one multi-turn conversation over one repository.
2. `AgentState`: LangGraph state for the current reasoning step.
3. `ToolCall`: one tool decision and execution result.
4. `Trace`: structured runtime history for debugging and evaluation.
5. `TaskStatus`: `running`, `completed`, `failed`, or `stopped`.

Runtime behavior:

1. Maintain multi-turn history.
2. Preserve short-term memory across follow-up questions.
3. Limit maximum tool calls.
4. Retry recoverable tool failures.
5. Stop with a clear reason when the Agent cannot continue.
6. Return trace data for observability and evaluation.

Expected resume evidence:

```text
Built an Agent Runtime with session management, multi-turn memory, task status tracking, failure retry, and structured traces.
```

### 4. API Service Layer

Responsible for making the project usable as a backend service.

Planned FastAPI endpoints:

1. `POST /repositories/index`
   - Build or refresh a repository index.
2. `POST /sessions`
   - Create a session bound to a repository path.
3. `POST /sessions/{session_id}/ask`
   - Ask a question in a session.
4. `GET /sessions/{session_id}`
   - Inspect session status, history, and latest answer.
5. `GET /tools`
   - List registered tools and permissions.
6. `GET /health`
   - Health check.

The existing CLI will remain available and should call the same service/runtime functions where practical.

Expected resume evidence:

```text
Exposed the Agent runtime through FastAPI APIs while preserving CLI compatibility.
```

### 5. Evaluation Layer

Responsible for quantifying whether the Agent works.

Evaluation data format:

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

Metrics:

1. Retrieval hit rate.
2. Tool-call accuracy.
3. Citation coverage.
4. Agent success rate.
5. Hallucination flag rate.

Hallucination control will start with deterministic checks:

1. If an answer mentions a file path that does not exist, flag it.
2. If an answer requires evidence but has no citation, flag it.
3. If expected files are not retrieved or cited, mark the case as partially failed.

Expected resume evidence:

```text
Built an automated evaluation set to measure retrieval hit rate, tool-call accuracy, citation coverage, Agent success rate, and hallucination risk.
```

### 6. Deployment and Showcase Layer

Responsible for making the project easy to run and present.

Deliverables:

1. Dockerfile.
2. Docker Compose file.
3. Structured logging.
4. Architecture diagram.
5. README rewrite.
6. Demo script.
7. Interview Q&A notes.
8. Resume bullet examples.

Expected resume evidence:

```text
Containerized the Agent service with Docker and documented architecture, demo workflows, evaluation results, and engineering trade-offs.
```

## Version Roadmap

### V5: RAG Tool Integration

Goal:

Connect the current RAG module to the Agent tool layer.

Scope:

1. Add `retrieve_code` as an Agent tool.
2. Return path, line range, content, and score.
3. Make the Agent choose between `search_code` and `retrieve_code`.
4. Require final answers to include citations when using retrieved code.
5. Add tests for retrieval tool execution and answer context flow.

Resume capability:

RAG, Tool Calling, citation-based hallucination control.

### V6: Agent Runtime and Session Memory

Goal:

Upgrade the Agent from a one-shot runner into a runtime.

Scope:

1. Add session model.
2. Add in-memory session store.
3. Preserve conversation history across turns.
4. Add structured trace records.
5. Add retry policy for failed tool execution.
6. Add clear stop reasons.

Resume capability:

Agent Runtime, session management, memory, failure handling, state management.

### V7: FastAPI Service

Goal:

Expose the runtime as a backend service.

Scope:

1. Add FastAPI dependency.
2. Add API schemas.
3. Add repository index endpoint.
4. Add session endpoints.
5. Add ask endpoint.
6. Add tool list and health endpoints.
7. Add API tests.

Resume capability:

Python backend, API development, service boundary, backend testing.

### V8: MCP-Style Tool Protocol

Goal:

Make tool registration explicit and extensible.

Scope:

1. Define `ToolSpec`.
2. Define input schema validation.
3. Define permission categories.
4. Refactor existing tools into the registry.
5. Add permission checks before execution.
6. Add tests for invalid parameters, unknown tools, and denied tools.

Resume capability:

MCP/tool ecosystem, plugin-like extensibility, permission control, tool sandbox boundary.

### V9: RAG and Agent Evaluation

Goal:

Add measurable quality evaluation.

Scope:

1. Add `eval_cases.jsonl`.
2. Add evaluation runner.
3. Measure retrieval hit rate.
4. Measure tool-call accuracy.
5. Measure citation coverage.
6. Add deterministic hallucination checks.
7. Generate JSON and Markdown evaluation reports.

Resume capability:

Agent evaluation, RAG evaluation, automated test set, hallucination control.

### V10: Engineering Packaging

Goal:

Make the project ready for GitHub, resume, and interview presentation.

Scope:

1. Add Dockerfile.
2. Add Docker Compose.
3. Add structured logging.
4. Rewrite README.
5. Add architecture diagram.
6. Add demo commands.
7. Add resume bullets.
8. Add interview Q&A.

Resume capability:

Docker, deployment, observability basics, documentation, project presentation.

## Non-Goals

The following are not planned for the next implementation cycle:

1. Training or fine-tuning models.
2. SFT, RLHF, DPO, PPO, Reward Model, LoRA, or QLoRA.
3. Multi-agent collaboration with role-based agents.
4. Real Kubernetes deployment.
5. Write access to the analyzed repository.
6. Browser or GUI automation.
7. Multi-modal input.

These topics can be mentioned as future directions, but they should not distract from making the core Agent platform solid.

## Acceptance Criteria

The redesigned project is considered resume-ready when:

1. A user can index a repository.
2. A user can create a session and ask follow-up questions.
3. The Agent can choose tools through LangGraph.
4. The Agent can use both keyword search and RAG retrieval.
5. Answers include citations when based on repository content.
6. Tool execution is validated and permission-checked.
7. Session history and traces can be inspected.
8. Evaluation can run from one command and produce metrics.
9. The service can run through Docker.
10. README explains architecture, usage, evaluation, limitations, and resume value.

## Suggested Resume Description

```text
Built Codebase Agent Platform, a LangGraph-based Agent Runtime for codebase understanding. The system supports repository indexing, RAG retrieval, Tool Calling, multi-turn session memory, MCP-style tool registration, permission checks, structured traces, and FastAPI service APIs. Added an automated evaluation set to measure retrieval hit rate, tool-call accuracy, citation coverage, Agent success rate, and hallucination risk, and containerized the service with Docker.
```

## Implementation Policy

Each version must include:

1. Focused implementation changes.
2. Unit or integration tests.
3. Documentation updates when user-facing behavior changes.
4. A runnable verification command.

The implementation order is V5 to V10. Later versions should not be started until the current version has tests and documentation.
