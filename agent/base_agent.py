from abc import ABC, abstractmethod

from models.task import Task
from models.agent_result import AgentResult
from models.task_execution_state import TaskExecutionState


class BaseAgent(ABC):

    def __init__(
        self,
        name: str,
        model_client,
        tools: dict
    ):
        self.name = name
        self.model_client = model_client
        self.tools = tools

    @abstractmethod
    async def run(
        self,
        task: Task,
        context: dict | None = None,
        state: TaskExecutionState | None = None
    ) -> AgentResult:
        pass