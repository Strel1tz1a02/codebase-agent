import src.graph.nodes as graph_nodes
from langchain_core.messages import ToolMessage
from src.graph.nodes import (
    execute_tools,
    finish,
    plan_next_step,
    plan_tool_use,
    retrieve_context,
    synthesize_answer,
    validate_answer,
)
from src.graph.state import create_initial_state


class FakeChatResponse:
    def __init__(self, content):
        self.content = content


class RecordingInvokeModel:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeChatResponse(self.response)


def assert_partial_update(result):
    assert "project_id" not in result
    assert "repo_path" not in result
    assert "chat_model" not in result
    assert "rag_index" not in result
    assert "tool_executor" not in result


def test_plan_next_step_uses_chat_model_invoke():
    state = create_initial_state("demo", "E:/repo", "Where is main?")
    model = RecordingInvokeModel("retrieve")
    state["chat_model"] = model

    result = plan_next_step(state)

    assert result["next_step"] == "retrieve"
    assert model.prompts
    assert "Where is main?" in model.prompts[0]
    assert "retrieve" in model.prompts[0]
    assert_partial_update(result)


def test_plan_next_step_keeps_unknown_model_plan_for_router_replan():
    state = create_initial_state("demo", "E:/repo", "Where is main?")
    state["chat_model"] = RecordingInvokeModel("maybe later")

    result = plan_next_step(state)

    assert result["next_step"] == "invalid"
    assert result["events"][-1] == {"type": "next_step_planned", "next_step": "invalid"}
    assert_partial_update(result)


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

    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], ToolMessage)
    assert result["messages"][0].name == "retrieve_context"
    assert "src/rag/retrieval.py" in result["messages"][0].content
    assert result["retrieval_round"] == 1
    assert calls == [
        {"rag_index": fake_index, "question": "Where is retrieval?", "top_k": 5}
    ]
    assert result["events"][-1] == {"type": "context_retrieved", "hit_count": 1}
    assert_partial_update(result)


def test_tool_planning_uses_chat_model_and_execution_uses_executor():
    state = create_initial_state("demo", "E:/repo", "List files")
    planned_calls = [{"name": "repo_summary", "arguments": {"path": "."}}]
    tool_results = [{"name": "repo_summary", "ok": True, "output": ["src/main.py"]}]
    state["chat_model"] = RecordingInvokeModel(
        '[{"name": "repo_summary", "arguments": {"path": "."}}]'
    )

    planned = plan_tool_use(state)
    execution_state = create_initial_state("demo", "E:/repo", "List files")
    execution_state["tool_calls"] = planned_calls
    execution_state["tool_executor"] = lambda call, current: tool_results[0]
    executed = execute_tools(execution_state)

    assert planned["tool_calls"] == planned_calls
    assert len(executed["messages"]) == 1
    assert isinstance(executed["messages"][0], ToolMessage)
    assert executed["messages"][0].name == "repo_summary"
    assert "src/main.py" in executed["messages"][0].content
    assert executed["tool_round"] == 1
    assert executed["events"][-1] == {"type": "tools_executed", "result_count": 1}
    assert_partial_update(planned)
    assert_partial_update(executed)


def test_plan_tool_use_uses_chat_model_invoke_json_calls():
    state = create_initial_state("demo", "E:/repo", "Read runtime file")
    model = RecordingInvokeModel(
        '[{"name": "read_file", "arguments": {"path": "src/runtime/runs.py"}}]'
    )
    state["chat_model"] = model
    state["messages"].append(
        {
            "role": "tool",
            "name": "retrieve_context",
            "content": "1. src/runtime/runs.py:0-0\nclass RuntimeService",
        }
    )

    result = plan_tool_use(state)

    assert result["tool_calls"] == [
        {"name": "read_file", "arguments": {"path": "src/runtime/runs.py"}}
    ]
    assert "Read runtime file" in model.prompts[0]
    assert "read_file" in model.prompts[0]
    assert_partial_update(result)


def test_synthesize_validate_and_finish_use_chat_model():
    state = create_initial_state("demo", "E:/repo", "Where is main?")
    state["chat_model"] = RecordingInvokeModel("main is in src/main.py")

    synthesized = synthesize_answer(state)
    validated = validate_answer(synthesized)
    finished = finish(validated)

    assert synthesized["answer"] == "main is in src/main.py"
    assert validated["status"] == "completed"
    assert finished["events"][-1] == {"type": "graph_finished", "status": "completed"}
    assert_partial_update(synthesized)
    assert_partial_update(validated)
    assert_partial_update(finished)


def test_validate_answer_fails_empty_answer():
    state = create_initial_state("demo", "E:/repo", "Where is main?")
    state["answer"] = "   "

    result = validate_answer(state)

    assert result["status"] == "failed"
    assert result["reason"] == "empty answer"
    assert result["events"][-1] == {"type": "answer_validated", "valid": False}
    assert_partial_update(result)


def test_synthesize_answer_uses_chat_model_invoke_with_retrieval_context():
    state = create_initial_state("demo", "E:/repo", "Where is retrieval?")
    model = RecordingInvokeModel("Retrieval is in src/rag/retrieval.py.")
    state["chat_model"] = model
    state["messages"].append(
        {
            "role": "tool",
            "name": "retrieve_context",
            "content": "1. src/rag/retrieval.py:10-20\ndef retrieve_from_index(...): pass",
        }
    )

    result = synthesize_answer(state)

    assert result["answer"] == "Retrieval is in src/rag/retrieval.py."
    assert "Where is retrieval?" in model.prompts[0]
    assert "src/rag/retrieval.py:10-20" in model.prompts[0]
    assert "def retrieve_from_index" in model.prompts[0]
    assert_partial_update(result)
