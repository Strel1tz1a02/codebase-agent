from src.graph.builder import build_graph
from src.graph.state import create_initial_state


class FakeChatResponse:
    def __init__(self, content):
        self.content = content


class SequencedInvokeModel:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeChatResponse(next(self.responses))


def _make_state(question, chat_model=None, rag_index=None, tool_executor=None):
    return create_initial_state(
        "demo", "E:/repo", question,
        rag_index=rag_index,
        chat_model=chat_model,
        tool_executor=tool_executor,
    )


def test_build_graph_returns_completed_answer():
    graph = build_graph()
    state = _make_state("hello")

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["answer"] == "Graph execution completed."


def test_build_graph_runs_retrieve_code_tool_and_answer_flow():
    """验证 graph 通过 retrieve_code 工具完成语义检索和回答流程。"""
    graph = build_graph()
    tool_calls = []

    def fake_tool_executor(name, args):
        """记录工具调用，并返回一个包含 RAG 命中文件的工具结果。"""
        tool_calls.append((name, args))
        return {
            "name": name,
            "ok": True,
            "output": {
                "matches": [
                    {
                        "relative_path": "src/rag/retrieval.py",
                        "content": "retrieval implementation",
                    }
                ]
            },
        }

    state = _make_state(
        "Where is retrieval?",
        chat_model=SequencedInvokeModel(
            [
                '[{"name": "retrieve_code", "arguments": {"repo_path": "E:/repo", "query": "Where is retrieval?", "top_k": 1}}]',
                "answer",
                "retrieval is in src/rag/retrieval.py",
            ]
        ),
        rag_index=object(),
        tool_executor=fake_tool_executor,
    )

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert "context" not in result
    assert tool_calls == [
        (
            "retrieve_code",
            {"repo_path": "E:/repo", "query": "Where is retrieval?", "top_k": 1},
        )
    ]
    assert any(
        getattr(message, "name", "") == "retrieve_code"
        and "src/rag/retrieval.py" in getattr(message, "content", "")
        for message in result["messages"]
    )
    assert result["answer"] == "retrieval is in src/rag/retrieval.py"
    assert [event["type"] for event in result["events"]] == [
        "next_step_planned",
        "tools_executed",
        "next_step_planned",
        "answer_synthesized",
        "answer_validated",
        "graph_finished",
    ]


def test_build_graph_can_call_retrieve_code_again_before_answering():
    """验证 graph 可多轮调用 retrieve_code 工具，再进入最终回答。"""
    graph = build_graph()
    tool_calls = []

    def fake_tool_executor(name, args):
        """记录 retrieve_code 工具调用顺序，并返回空命中结果。"""
        tool_calls.append((name, args))
        return {"name": name, "ok": True, "output": {"matches": []}}

    state = _make_state(
        "Where is config?",
        chat_model=SequencedInvokeModel(
            [
                '[{"name": "retrieve_code", "arguments": {"repo_path": "E:/repo", "query": "config", "top_k": 1}}]',
                '[{"name": "retrieve_code", "arguments": {"repo_path": "E:/repo", "query": "config fallback", "top_k": 1}}]',
                "answer",
                "answered after 2 retrievals",
            ]
        ),
        rag_index=object(),
        tool_executor=fake_tool_executor,
    )

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["tool_round"] == 2
    assert [name for name, _ in tool_calls] == ["retrieve_code", "retrieve_code"]
    assert result["answer"] == "answered after 2 retrievals"


def test_build_graph_retries_once_after_unknown_next_step():
    graph = build_graph()
    model = SequencedInvokeModel(["maybe later", "answer", "corrected answer"])
    state = _make_state(
        "Where is main?",
        chat_model=model,
    )

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["answer"] == "corrected answer"
    assert "maybe later" in model.prompts[1]
    assert any(
        getattr(message, "name", "") == "invalid_plan"
        and getattr(message, "content", "") == "maybe later"
        for message in result["messages"]
    )
    assert [event["type"] for event in result["events"]] == [
        "next_step_planned",
        "next_step_planned",
        "answer_synthesized",
        "answer_validated",
        "graph_finished",
    ]


def test_build_graph_falls_back_after_invalid_plan_limit():
    graph = build_graph()
    state = _make_state(
        "Where is main?",
        chat_model=SequencedInvokeModel(
            ["maybe later", "still invalid", "fallback answer"]
        ),
    )

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["answer"] == "fallback answer"
    assert result["invalid_plan_round"] == 2
    assert [event["type"] for event in result["events"]] == [
        "next_step_planned",
        "next_step_planned",
        "answer_synthesized",
        "answer_validated",
        "graph_finished",
    ]
