from langgraph.graph import END

from src.graph.routing import (
    route_after_finish,
    route_after_plan,
    route_after_retrieval,
    route_after_synthesis,
    route_after_tool_plan,
    route_after_tool_execution,
    route_after_validation,
)


def test_route_after_plan_selects_retrieve_tools_or_answer():
    assert route_after_plan({"next_step": "retrieve"}) == "retrieve_context"
    assert route_after_plan({"next_step": "tool"}) == "plan_tool_use"
    assert route_after_plan({"next_step": "answer"}) == "synthesize_answer"


def test_route_after_plan_replans_unknown_next_step():
    assert route_after_plan({"next_step": "unknown"}) == "plan_next_step"
    assert route_after_plan({"next_step": ""}) == "plan_next_step"


def test_route_after_plan_uses_round_limits_to_prevent_loops():
    assert (
        route_after_plan(
            {
                "next_step": "retrieve",
                "retrieval_round": 2,
                "max_retrieval_rounds": 2,
            }
        )
        == "synthesize_answer"
    )
    assert (
        route_after_plan(
            {
                "next_step": "tool",
                "tool_round": 3,
                "max_tool_rounds": 3,
            }
        )
        == "synthesize_answer"
    )


def test_react_observation_routes_return_to_plan_next_step():
    assert route_after_retrieval({}) == "plan_next_step"
    assert route_after_tool_execution({}) == "plan_next_step"


def test_route_after_tool_plan_always_executes_tools():
    assert route_after_tool_plan({"tool_calls": []}) == "execute_tools"
    assert route_after_tool_plan({"tool_calls": [{"name": "repo_summary"}]}) == "execute_tools"


def test_late_routes_validate_finish_and_end():
    assert route_after_synthesis({}) == "validate_answer"
    assert route_after_validation({}) == "finish"
    assert route_after_finish({"status": "completed"}) == END
