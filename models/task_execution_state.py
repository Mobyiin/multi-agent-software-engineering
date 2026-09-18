from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskExecutionState:
    task_id: str

    status: str = "pending"
    current_iteration: int = 0

    last_action: str | None = None
    last_tool: str | None = None
    last_tool_result: Any = None

    completed_steps: list[str] = field(
        default_factory=list
    )

    modified_files: list[str] = field(
        default_factory=list
    )

    test_status: str | None = None
    retry_count: int = 0