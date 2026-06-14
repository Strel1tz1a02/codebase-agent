import src.graph.nodes as graph_nodes
from src.graph.nodes import (
    execute_tools,
    finish,
    plan_next_step,
    plan_tool_use,
    prepare_context,
    retrieve_context,
    synthesize_answer,
    validate_answer,
)
from src.graph.state import create_initial_state


def test_prepare_context_records_question_and_repo():
    state = create_initial_state("demo", "E:/repo", "Where is main?")

    result = prepare_context(state)

    assert result["context"]["question"] == "Where is main?"
    assert result["context"]["repo_path"] == "E:/repo"
    assert result["events"][-1]["type"] == "context_prepared"


def test_plan_next_step_uses_fake_planner():
    state = create_initial_state("demo", "E:/repo", "Where is main?")
    state["step_planner"] = lambda current: "retrieve"

    result = plan_next_step(state)

    assert result["next_step"] == "retrieve"
    assert result["events"][-1] == {"type": "next_step_planned", "next_step": "retrieve"}


def test_retrieve_context_uses_rag_index(monkeypatch):
    state = create_initial_state("demo", "E:/repo", "Where is retrieval?")
    fake_hits = [{"relative_path": "src/rag/retrieval.py", "content": "retrieve"}]
    fake_index = object()
    calls = []

    def fake_retrieve_from_index(rag_index, question, top_k):
        calls.append({"rag_index": rag_index, "question": question, "top_k": top_k})
        return fake_hits

    monkeypatch.setattr(graph_nodes, "retrieve_from_index", fake_retrieve_from_index)
    state["rag_index"] = fake_index

    result = retrieve_context(state)

    assert result["retrieval_hits"] == fake_hits
    assert calls == [
        {"rag_index": fake_index, "question": "Where is retrieval?", "top_k": 5}
    ]
    assert result["events"][-1] == {"type": "context_retrieved", "hit_count": 1}


def test_tool_planning_and_execution_use_fake_dependencies():
    state = create_initial_state("demo", "E:/repo", "List files")
    planned_calls = [{"name": "list_files", "arguments": {"path": "."}}]
    tool_results = [{"name": "list_files", "ok": True, "output": ["src/main.py"]}]
    state["tool_planner"] = lambda current: planned_calls
    state["tool_executor"] = lambda call, current: tool_results[0]

    planned = plan_tool_use(state)
    executed = execute_tools(planned)

    assert planned["tool_calls"] == planned_calls
    assert executed["tool_results"] == tool_results
    assert executed["events"][-1] == {"type": "tools_executed", "result_count": 1}


def test_synthesize_validate_and_finish_use_fake_chat_and_validator():
    state = create_initial_state("demo", "E:/repo", "Where is main?")
    state["chat_model"] = lambda current: "main is in src/main.py"
    state["answer_validator"] = lambda answer, current: (True, "")

    synthesized = synthesize_answer(state)
    validated = validate_answer(synthesized)
    finished = finish(validated)

    assert synthesized["answer"] == "main is in src/main.py"
    assert validated["status"] == "completed"
    assert finished["events"][-1] == {"type": "graph_finished", "status": "completed"}
