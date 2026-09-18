from dataclasses import dataclass, field

from models.agent_result import AgentResult


@dataclass
class WorkflowResult:

    success: bool
    status: str
    results: list[AgentResult] = field(default_factory=list)
    error: str | None = None