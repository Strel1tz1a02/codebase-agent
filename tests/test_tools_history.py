from src.runtime.run import Run
from src.runtime.session import RuntimeSession
from src.tools.history import READ_HISTORY_RUN_TOOL_NAME, read_history_run
from src.tools.toolkit import ToolContext, execute_tool


def test_read_history_run_reads_current_session_run():
    session = RuntimeSession(session_id="session-1")
    session.add_run(Run(run_id="run-1", question="old question", answer="old answer", status="completed"))

    result = read_history_run(session, "run-1")

    assert result["run_id"] == "run-1"
    assert result["question"] == "old question"
    assert result["answer"] == "old answer"


def test_read_history_run_uses_read_history_run_tool_name():
    session = RuntimeSession(session_id="session-1")
    session.add_run(Run(run_id="run-1", question="old question", answer="old answer", status="completed"))

    assert READ_HISTORY_RUN_TOOL_NAME == "read_history_run"
    assert read_history_run(session, "run-1")["run_id"] == "run-1"


def test_execute_tool_reads_history_run_with_session_context():
    session = RuntimeSession(session_id="session-1")
    session.add_run(Run(run_id="run-1", question="old question", answer="old answer", status="completed"))

    result = execute_tool(
        READ_HISTORY_RUN_TOOL_NAME,
        {"run_id": "run-1"},
        context=ToolContext(session=session),
    )

    assert result.ok is True
    assert result.output["session_id"] == "session-1"
    assert result.output["run_id"] == "run-1"
    assert result.output["question"] == "old question"
    assert result.output["answer"] == "old answer"


def test_execute_tool_rejects_history_run_without_session_context():
    result = execute_tool(READ_HISTORY_RUN_TOOL_NAME, {"run_id": "run-1"})

    assert result.ok is False
    assert "session context required" in result.error
