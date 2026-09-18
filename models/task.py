from dataclasses import dataclass, field
from models.agent_result import AgentResult


@dataclass
class Task:
    id: str
    description: str
    status: str = "pending"
    assigned_agent: str | None = None
    retries: int = 0
    dependencies: list[str] = field(default_factory=list)
    result: AgentResult | None = None
    error: str | None = None
    max_iterations: int = 10

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be greater than 0.")