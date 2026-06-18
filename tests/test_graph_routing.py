from langgraph.graph import END

from src.graph.routing import (
    route_after_finish,
    route_after_plan,
    route_after_synthesis,
    route_after_tool_execution,
    route_after_validation,
)


def test_route_after_plan_selects_tools_or_answer():
    assert route_after_plan({"next_step": "execute_tools"}) == "execute_tools"
    assert route_after_plan({"next_step": "answer"}) == "synthesize_answer"


def test_route_after_plan_retries_unknown_next_step_until_limit():
    assert (
        route_after_plan(
            {
                "next_step": "unknown",
                "invalid_plan_round": 1,
                "max_invalid_plan_rounds": 2,
            }
        )
        == "plan_next_step"
    )
    assert (
        route_after_plan(
            {
                "next_step": "",
                "invalid_plan_round": 2,
                "max_invalid_plan_rounds": 2,
            }
        )
        == "synthesize_answer"
    )


def test_route_after_plan_uses_round_limits_to_prevent_loops():
    assert (
        route_after_plan(
            {
                "next_step": "execute_tools",
                "tool_round": 3,
                "max_tool_rounds": 3,
            }
        )
        == "synthesize_answer"
    )


def test_tool_observation_routes_return_to_plan_next_step():
    assert route_after_tool_execution({}) == "plan_next_step"


def test_late_routes_validate_finish_and_end():
    assert route_after_synthesis({}) == "validate_answer"
    assert route_after_validation({}) == "finish"
    assert route_after_finish({"status": "completed"}) == END
