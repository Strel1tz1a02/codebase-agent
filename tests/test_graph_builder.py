import src.graph.nodes as graph_nodes
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


def test_build_graph_runs_retrieve_tool_and_answer_flow_with_fake_dependencies(monkeypatch):
    graph = build_graph()
    state = _make_state(
        "Where is retrieval?",
        chat_model=SequencedInvokeModel(
            [
                "retrieve",
                '[{"name": "inspect_hit", "arguments": {"path": "src/rag/retrieval.py"}}]',
                "answer",
                "retrieval is in src/rag/retrieval.py",
            ]
        ),
        rag_index=object(),
        tool_executor=lambda name, args: {
            "name": name,
            "ok": True,
            "output": "inspected",
        },
    )
    monkeypatch.setattr(
        graph_nodes,
        "retrieve_from_index",
        lambda rag_index, question, top_k: [
            {"relative_path": "src/rag/retrieval.py", "content": question}
        ],
    )

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert "context" not in result
    assert any(
        getattr(message, "name", "") == "retrieve_context"
        and "src/rag/retrieval.py" in getattr(message, "content", "")
        for message in result["messages"]
    )
    assert any(
        getattr(message, "name", "") == "inspect_hit"
        and "inspected" in getattr(message, "content", "")
        for message in result["messages"]
    )
    assert result["answer"] == "retrieval is in src/rag/retrieval.py"
    assert [event["type"] for event in result["events"]] == [
        "next_step_planned",
        "context_retrieved",
        "next_step_planned",
        "tools_executed",
        "next_step_planned",
        "answer_synthesized",
        "answer_validated",
        "graph_finished",
    ]


def test_build_graph_can_retrieve_again_before_answering(monkeypatch):
    graph = build_graph()
    state = _make_state(
        "Where is config?",
        chat_model=SequencedInvokeModel(
            ["retrieve", "retrieve", "answer", "answered after 2 retrievals"]
        ),
        rag_index=object(),
    )
    retrieval_calls = []

    def fake_retrieve_from_index(rag_index, question, top_k):
        retrieval_calls.append((rag_index, question, top_k))
        return [
            {
                "relative_path": f"src/config_{len(retrieval_calls)}.py",
                "content": question,
            }
        ]

    monkeypatch.setattr(graph_nodes, "retrieve_from_index", fake_retrieve_from_index)

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["retrieval_round"] == 1
    assert len(retrieval_calls) == 1
    assert retrieval_calls[0][0] is state["rag_index"]
    assert result["answer"] == "answer"


def test_build_graph_replans_after_unknown_next_step():
    graph = build_graph()
    state = _make_state(
        "Where is main?",
        chat_model=SequencedInvokeModel(
            ["maybe later", "answer", "main is in src/main.py"]
        ),
    )

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["answer"] == "main is in src/main.py"
    assert [event["type"] for event in result["events"]] == [
        "next_step_planned",
        "next_step_planned",
        "answer_synthesized",
        "answer_validated",
        "graph_finished",
    ]
