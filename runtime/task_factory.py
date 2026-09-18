from itertools import count

from models.manager_plan import TaskProposal
from models.task import Task


class TaskFactory:

    def __init__(self,worker_start: int = 1,manager_start: int = 1):

        self._worker_counter = count(worker_start)
        self._manager_counter = count(manager_start)

    def next_task_id(self) -> str:

        number = next(self._worker_counter)

        return f"T{number:03d}"

    def next_manager_id(self) -> str:

        number = next(self._manager_counter)

        return f"MANAGER-{number:03d}"

    def _get_iteration_budget(
        self,
        complexity: str
    ) -> int:

        budgets = {
            "small": 8,
            "medium": 15,
            "large": 25
        }

        if complexity not in budgets:
            raise ValueError(
                f"Unknown complexity: "
                f"{complexity}"
            )

        return budgets[complexity]

    def create_from_proposal(
        self,
        proposal: TaskProposal
    ) -> Task:

        return Task(
            id=self.next_task_id(),
            description=proposal.description,
            assigned_agent=(proposal.assigned_agent),
            max_iterations=(self._get_iteration_budget(proposal.complexity))
        )