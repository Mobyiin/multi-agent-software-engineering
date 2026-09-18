import inspect
import time

from models.tool_execution_result import ToolExecutionResult


from observability.events import Event
from observability.logger import event_logger


def execute_tool(
    tools: dict,
    tool_name: str,
    arguments: dict,
    task_id: str | None = None,
    agent_id: str | None = None
) -> ToolExecutionResult:


    if tool_name not in tools:

        event_logger.emit(
            Event(
                event_type="tool_rejected",
                task_id=task_id,
                agent_id=agent_id,
                tool_name=tool_name,
                success=False,
                message="Tool is not allowed.",
                data={"arguments": arguments}
            )
        )

        return ToolExecutionResult(
            success=False,
            tool_name=tool_name,
            error=(f"Tool '{tool_name}' is not allowed.")
        )

    tool = tools[tool_name]


    try:

        signature = inspect.signature(tool)

        signature.bind(**arguments)

    except TypeError as error:

        event_logger.emit(
            Event(
                event_type="tool_invalid_arguments",
                task_id=task_id,
                agent_id=agent_id,
                tool_name=tool_name,
                success=False,
                message=str(error),
                data={"arguments": arguments}
            )
        )

        return ToolExecutionResult(
            success=False,
            tool_name=tool_name,
            error=(f"Invalid arguments: {error}")
        )


    event_logger.emit(
        Event(
            event_type="tool_started",
            task_id=task_id,
            agent_id=agent_id,
            tool_name=tool_name,
            message="Executing tool.",
            data={"arguments": arguments}
        )
    )

    start_time = time.perf_counter()

    try:

        result = tool(**arguments)

        latency_ms = (time.perf_counter() - start_time) * 1000

        event_logger.emit(
            Event(
                event_type="tool_completed",
                task_id=task_id,
                agent_id=agent_id,
                tool_name=tool_name,
                success=True,
                latency_ms=latency_ms,
                message="Tool succeeded."
            )
        )

        return ToolExecutionResult(
            success=True,
            tool_name=tool_name,
            result=result
        )

    except Exception as error:
        latency_ms = (time.perf_counter() - start_time) * 1000

        event_logger.emit(
            Event(
                event_type="tool_failed",
                task_id=task_id,
                agent_id=agent_id,
                tool_name=tool_name,
                success=False,
                latency_ms=latency_ms,
                message=str(error)
            )
        )

        return ToolExecutionResult(
            success=False,
            tool_name=tool_name,
            error=str(error)
        )
