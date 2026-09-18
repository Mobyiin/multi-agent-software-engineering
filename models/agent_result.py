from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    success: bool
    agent_name: str
    task_id: str
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
