from dataclasses import dataclass
from typing import Any


@dataclass
class ToolExecutionResult:
    success: bool
    tool_name: str
    result: Any = None
    error: str | None = None
