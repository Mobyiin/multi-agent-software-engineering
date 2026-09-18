from models.task import Task

from runtime.task_factory import TaskFactory


class ChatSession:

    def __init__(
        self,
        manager_agent,
        workflow_runner,
        task_factory: TaskFactory
    ):
        self.manager_agent = manager_agent

        self.workflow_runner = workflow_runner

        self.task_factory = task_factory

    async def handle_message(self,message: str) -> dict:

        manager_task = Task(
            id=self.task_factory.next_manager_id(),
            description=message,
            max_iterations=5
        )

        manager_result = await self.manager_agent.run(task=manager_task)

        if not manager_result.success:

            return {
                "success": False,
                "manager_result":
                manager_result,
                "plan": None,
                "workflow": None,
            }

        plan = manager_result.data.get("plan")

        if plan is None:

            return {
                "success": False,
                "manager_result":manager_result,
                "plan": None,
                "workflow": None,
            }

        workflow = await self.workflow_runner.run(original_goal=message,initial_plan=plan)

        return {
            "success": workflow.success,
            "manager_result": manager_result,
            "plan": plan,
            "workflow": workflow
        }
    
    async def run_cli(self) -> None:

        print("\nMulti-Agent Software Engineering System")

        print("Write your request over multiple lines.")

        print("Type END on a separate line to submit.")

        print("Type exit or quit before a request to stop.")

        while True:

            print("\nYou:")

            lines: list[str] = []

            while True:

                line = input()
                normalized = line.strip()

                if (not lines and normalized.lower() in {"exit","quit"}):

                    print("\nProgram stopped by user.")

                    return

                if (normalized == "END"):
                    break

                lines.append(line)

            message = "\n".join(lines).strip()

            if not message:
                continue

            result = await self.handle_message(message)

            manager_result = result["manager_result"]

            if (not manager_result.success):

                print("\nManager blocked:")

                print(manager_result.error)

                continue

            plan = result["plan"]

            print("\nManager plan:")

            print(plan.goal_summary)

            for proposal in (plan.tasks):

                print(
                    "- "
                    f"{proposal.assigned_agent}: "
                    f"{proposal.description}"
                )

            workflow = result["workflow"]

            if workflow is None:

                print("\nNo workflow generated.")

                continue

            print(f"\nWorkflow status: {workflow.status}")


            if (workflow.success and workflow.status == "ready_for_approval"):

                print("\nWork completed.")

                print("The staged project is ready for approval.")

                print("The original workspace has not been modified.")

                return

            print("\nWorkflow is blocked.")

            print("The application is still running.")

            if workflow.error:

                print(workflow.error)