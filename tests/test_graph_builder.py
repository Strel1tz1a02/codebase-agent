import src.graph.nodes as graph_nodes
from src.graph.builder import build_graph
from src.graph.state import create_initial_state


def test_build_graph_returns_completed_answer():
    graph = build_graph()
    state = create_initial_state("demo", "E:/repo", "hello")

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["answer"] == "Graph execution completed."


def test_build_graph_runs_retrieve_tool_and_answer_flow_with_fake_dependencies(monkeypatch):
    graph = build_graph()
    state = create_initial_state("demo", "E:/repo", "Where is retrieval?")
    next_steps = iter(["retrieve", "tool", "answer"])
    state["step_planner"] = lambda current: next(next_steps)
    state["rag_index"] = object()
    monkeypatch.setattr(
        graph_nodes,
        "retrieve_from_index",
        lambda rag_index, question, top_k: [
            {"relative_path": "src/rag/retrieval.py", "content": question}
        ],
    )
    state["tool_planner"] = lambda current: [
        {"name": "inspect_hit", "arguments": {"path": "src/rag/retrieval.py"}}
    ]
    state["tool_executor"] = lambda call, current: {
        "name": call["name"],
        "ok": True,
        "output": "inspected",
    }
    state["chat_model"] = lambda current: "retrieval is in src/rag/retrieval.py"

    result = graph.invoke(state)

    assert result["status"] == "completed"
    assert result["retrieval_hits"][0]["relative_path"] == "src/rag/retrieval.py"
    assert result["tool_results"] == [
        {"name": "inspect_hit", "ok": True, "output": "inspected"}
    ]
    assert result["answer"] == "retrieval is in src/rag/retrieval.py"
    assert [event["type"] for event in result["events"]] == [
        "context_prepared",
        "next_step_planned",
        "context_retrieved",
        "next_step_planned",
        "tool_use_planned",
        "tools_executed",
        "next_step_planned",
        "answer_synthesized",
        "answer_validated",
        "graph_finished",
    ]


def test_build_graph_can_retrieve_again_before_answering(monkeypatch):
    graph = build_graph()
    state = create_initial_state("demo", "E:/repo", "Where is config?")
    next_steps = iter(["retrieve", "retrieve", "answer"])
    state["step_planner"] = lambda current: next(next_steps)
    state["chat_model"] = lambda current: (
        f"answered after {current['retrieval_round']} retrievals"
    )
    retrieval_calls = []

    fake_index = object()
    state["rag_index"] = fake_index

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
    assert result["retrieval_round"] == 2
    assert len(retrieval_calls) == 2
    assert retrieval_calls[0][0] is fake_index
    assert result["answer"] == "answered after 2 retrievals"
