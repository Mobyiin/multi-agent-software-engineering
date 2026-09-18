from models.manager_plan import ManagerPlan
from models.task import Task

from runtime.task_factory import TaskFactory



class RepairPlanner:

    def __init__(
        self,
        manager_agent,
        task_factory: TaskFactory
    ):
        self.manager_agent = manager_agent
    
        self.task_factory =  task_factory

    async def create_repair_plan(
        self,
        original_goal: str,
        problem_report: str
    ) -> ManagerPlan:

        manager_task = Task(
            id=self.task_factory.next_manager_id(),
            description=(
                "Create a focused repair plan "
                "for the current staged project."
                "\n\n"
                "Original user goal:\n"
                f"{original_goal}"
                "\n\n"
                "Problem report:\n"
                f"{problem_report}"
                "\n\n"
                "Create only the implementation "
                "tasks required to resolve these "
                "problems. Do not repeat work "
                "that is already correct."
            ),
            max_iterations=5
        )

        result = await self.manager_agent.run(task=manager_task)

        if not result.success:

            raise RuntimeError(
                result.error
                or 
                ("Manager failed to create repair plan.")
            )

        plan = result.data.get("plan")

        if plan is None:

            raise RuntimeError("Manager returned no repair plan.")

        if not isinstance(plan,ManagerPlan):
            raise TypeError("Manager repair result is not a ManagerPlan.")

        return plan