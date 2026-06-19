from src.graph.state import create_initial_state


def test_create_initial_state_sets_project_and_question():
    state = create_initial_state(
        project_id="demo",
        repo_path="E:/repo",
        question="Where is the entry point?",
        rag_index=None,
        chat_model=None,
        tool_executor=None,
        memory_summary="remembered facts",
        recent_history="user: previous",
    )

    assert state["project_id"] == "demo"
    assert state["repo_path"] == "E:/repo"
    assert state["messages"] == [
        {"role": "user", "content": "Where is the entry point?"}
    ]
    assert "context" not in state
    assert state.get("tool_calls", []) == []
    assert state["tool_round"] == 0
    assert state["max_tool_rounds"] == 5
    assert state["answer"] == ""
    assert state["status"] == "running"
    assert state["reason"] == ""
    assert state["events"] == []
    assert state["memory_summary"] == "remembered facts"
    assert state["recent_history"] == "user: previous"
