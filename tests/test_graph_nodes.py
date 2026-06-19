from langchain_core.messages import SystemMessage, ToolMessage
from src.graph.nodes import (
    execute_tools,
    finish,
    plan_next_step,
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


class RaisingInvokeModel:
    def __init__(self, error):
        self.error = error
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        raise self.error


class FakeToolCallResponse:
    def __init__(self, tool_calls=None, content=""):
        self.tool_calls = tool_calls or []
        self.content = content


class RecordingBindToolsModel:
    def __init__(self, response):
        self.response = response
        self.bound_tools = []
        self.prompts = []

    def bind_tools(self, tools):
        self.bound_tools.append(tools)
        return self

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.response


def assert_partial_update(result):
    assert "project_id" not in result
    assert "repo_path" not in result
    assert "chat_model" not in result
    assert "rag_index" not in result
    assert "tool_executor" not in result


def _make_state(question, chat_model=None):
    state = create_initial_state("demo", "E:/repo", question, rag_index=None, chat_model=chat_model, tool_executor=None)
    if chat_model is not None:
        state["chat_model"] = chat_model
    return state


def test_plan_next_step_rejects_bare_retrieve():
    """验证裸 retrieve 不再是合法规划结果，必须改用 retrieve_code 工具 JSON。"""
    model = RecordingInvokeModel("retrieve")
    state = _make_state("Where is main?", model)

    result = plan_next_step(state)

    assert result["next_step"] == "invalid"
    assert result["invalid_plan_round"] == 1
    assert "tool_calls" not in result
    assert model.prompts
    assert "Where is main?" in model.prompts[0]
    assert_partial_update(result)


def test_plan_next_step_selects_answer():
    state = _make_state("Where is main?", RecordingInvokeModel("answer"))

    result = plan_next_step(state)

    assert result["next_step"] == "answer"
    assert_partial_update(result)


def test_plan_next_step_reports_llm_error_without_empty_answer():
    state = _make_state("Where is main?", RaisingInvokeModel(RuntimeError("quota exceeded")))

    result = plan_next_step(state)

    assert result["status"] == "failed"
    assert result["reason"] == "llm_error: quota exceeded"
    assert result["events"][-1] == {
        "type": "llm_error",
        "stage": "plan_next_step",
        "error": "quota exceeded",
    }
    assert_partial_update(result)


def test_plan_next_step_uses_bound_tool_calls_when_supported():
    model = RecordingBindToolsModel(
        FakeToolCallResponse(
            [
                {
                    "name": "read_file",
                    "args": {"path": "src/graph/nodes.py"},
                    "id": "call-1",
                }
            ]
        )
    )
    state = _make_state("Read graph nodes", model)

    result = plan_next_step(state)

    assert result["next_step"] == "execute_tools"
    assert result["invalid_plan_round"] == 0
    assert result["tool_calls"] == [
        {"name": "read_file", "arguments": {"path": "src/graph/nodes.py"}}
    ]
    assert {tool.name for tool in model.bound_tools[0]} == {
        "repo_summary",
        "read_file",
        "search_code",
        "retrieve_code",
        "read_history_run",
    }
    assert "Read graph nodes" in model.prompts[0]
    assert_partial_update(result)


def test_bound_tool_model_is_reused_across_planning_rounds():
    model = RecordingBindToolsModel(FakeToolCallResponse(content="answer"))
    state = _make_state("Can we answer?", model)

    first = plan_next_step(state)
    second_state = {**state, **first}
    second = plan_next_step(second_state)

    assert first["next_step"] == "answer"
    assert second["next_step"] == "answer"
    assert len(model.bound_tools) == 1
    assert len(model.prompts) == 2


def test_plan_next_step_replans_unknown():
    model = RecordingInvokeModel("maybe later")
    state = _make_state("Where is main?", model)

    result = plan_next_step(state)

    assert result["next_step"] == "invalid"
    assert result["invalid_plan_round"] == 1
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], SystemMessage)
    assert result["messages"][0].name == "invalid_plan"
    assert result["messages"][0].content == "maybe later"
    assert result["events"][-1] == {"type": "next_step_planned", "next_step": "invalid"}
    assert_partial_update(result)


def test_plan_next_step_prompt_includes_previous_invalid_output():
    model = RecordingInvokeModel("answer")
    state = _make_state("Where is main?", model)
    state["invalid_plan_round"] = 1
    state["messages"].append(SystemMessage(content="maybe later", name="invalid_plan"))

    result = plan_next_step(state)

    assert result["next_step"] == "answer"
    assert result["invalid_plan_round"] == 0
    assert "上一轮规划输出格式无效" in model.prompts[0]
    assert "maybe later" in model.prompts[0]
    assert_partial_update(result)


def test_plan_next_step_parses_json_as_tool_calls():
    model = RecordingInvokeModel(
        '[{"name": "read_file", "arguments": {"path": "src/runtime/runs.py"}}]'
    )
    state = _make_state("Read runtime file", model)
    state["messages"].append(
        {
            "role": "tool",
            "name": "retrieve_code",
            "content": "1. src/runtime/runs.py:0-0\nclass RuntimeService",
        }
    )

    result = plan_next_step(state)

    assert result["next_step"] == "execute_tools"
    assert result["invalid_plan_round"] == 0
    assert result["tool_calls"] == [
        {"name": "read_file", "arguments": {"path": "src/runtime/runs.py"}}
    ]
    assert result["events"][-1] == {
        "type": "next_step_planned",
        "next_step": "execute_tools",
        "call_count": 1,
    }
    assert "Read runtime file" in model.prompts[0]
    assert "read_file" in model.prompts[0]
    assert_partial_update(result)


def test_plan_next_step_tool_calls_flow_to_execution():
    state = _make_state("List files", RecordingInvokeModel(
        '[{"name": "repo_summary", "arguments": {"path": "."}}]'
    ))

    planned = plan_next_step(state)

    assert planned["next_step"] == "execute_tools"
    execution_state = _make_state("List files")
    execution_state["tool_calls"] = planned["tool_calls"]
    execution_state["tool_executor"] = lambda name, args: {"name": "repo_summary", "ok": True, "output": ["src/main.py"]}
    executed = execute_tools(execution_state)

    assert len(executed["messages"]) == 1
    assert isinstance(executed["messages"][0], ToolMessage)
    assert executed["messages"][0].name == "repo_summary"
    assert executed["tool_round"] == 1
    assert executed["events"][-1] == {"type": "tools_executed", "result_count": 1}
    assert_partial_update(planned)
    assert_partial_update(executed)


def test_synthesize_validate_and_finish_use_chat_model():
    state = _make_state("Where is main?", RecordingInvokeModel("main is in src/main.py"))

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
    state = _make_state("Where is main?")
    state["answer"] = "   "

    result = validate_answer(state)

    assert result["status"] == "failed"
    assert result["reason"] == "empty answer"
    assert result["events"][-1] == {"type": "answer_validated", "valid": False}
    assert_partial_update(result)


def test_validate_answer_preserves_existing_failure_reason():
    state = _make_state("Where is main?")
    state["status"] = "failed"
    state["reason"] = "llm_error: quota exceeded"
    state["answer"] = ""

    result = validate_answer(state)

    assert result["status"] == "failed"
    assert result["reason"] == "llm_error: quota exceeded"
    assert result["events"][-1] == {"type": "answer_validated", "valid": False}
    assert_partial_update(result)


def test_synthesize_answer_reports_llm_error():
    state = _make_state("Where is main?", RaisingInvokeModel(RuntimeError("quota exceeded")))

    result = synthesize_answer(state)

    assert result["status"] == "failed"
    assert result["reason"] == "llm_error: quota exceeded"
    assert result["answer"] == ""
    assert result["events"][-1] == {
        "type": "llm_error",
        "stage": "synthesize_answer",
        "error": "quota exceeded",
    }
    assert_partial_update(result)


def test_finish_marks_running_state_failed():
    """验证 finish 会把未收束的 running 状态标记为失败，暴露异常路径。"""
    state = _make_state("Where is main?")

    result = finish(state)

    assert result["status"] == "failed"
    assert result["reason"] == "graph finished without terminal status"
    assert result["events"][-1] == {"type": "graph_finished", "status": "failed"}
    assert_partial_update(result)


def test_synthesize_answer_uses_chat_model_invoke_with_retrieval_context():
    model = RecordingInvokeModel("Retrieval is in src/rag/retrieval.py.")
    state = _make_state("Where is retrieval?", model)
    state["messages"].append(
        {
            "role": "tool",
            "name": "retrieve_code",
            "content": "1. src/rag/retrieval.py:10-20\ndef retrieve_from_index(...): pass",
        }
    )

    result = synthesize_answer(state)

    assert result["answer"] == "Retrieval is in src/rag/retrieval.py."
    assert "Where is retrieval?" in model.prompts[0]
    assert "src/rag/retrieval.py:10-20" in model.prompts[0]
    assert "def retrieve_from_index" in model.prompts[0]
    assert_partial_update(result)
