from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelResponse:
    content: str = ""
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    tool_call_id: str | None = None
    is_final: bool = False
