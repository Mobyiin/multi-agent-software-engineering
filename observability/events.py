from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class Event:
    event_type: str
    task_id: str | None = None
    agent_id: str | None = None
    sender: str | None = None
    receiver: str | None = None
    message: str = ""
    tool_name: str | None = None
    success: bool | None = None
    decision: str | None = None
    confidence: float | None = None
    retry_count: int = 0
    latency_ms: float | None = None
    tokens: int | None = None
    cost: float | None = None
    conflict_count: int = 0
    final_outcome: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(     
        default_factory=lambda: (
            datetime.now(timezone.utc).isoformat()
        )
    )
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
