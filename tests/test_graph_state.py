from src.graph.state import create_initial_state


def test_create_initial_state_sets_project_and_question():
    state = create_initial_state(
        project_id="demo",
        repo_path="E:/repo",
        question="Where is the entry point?",
    )

    assert state["project_id"] == "demo"
    assert state["repo_path"] == "E:/repo"
    assert state["messages"] == [
        {"role": "user", "content": "Where is the entry point?"}
    ]
    assert state["retrieval_hits"] == []
    assert state["tool_calls"] == []
    assert state["tool_results"] == []
    assert state["answer"] == ""
    assert state["status"] == "running"
    assert state["reason"] == ""
    assert state["events"] == []
