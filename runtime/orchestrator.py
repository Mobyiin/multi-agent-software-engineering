from models.agent_result import AgentResult
from models.manager_plan import TaskProposal
from models.task import Task
from models.task_execution_state import TaskExecutionState


from runtime.agent_registry import AgentRegistry
from runtime.task_factory import TaskFactory



class Orchestrator:

    def __init__(
        self,
        agent_registry: AgentRegistry,
        task_factory: TaskFactory,
        checkpoint_store=None,
    ):
        self.agent_registry = agent_registry
        self.task_factory = task_factory
        self.checkpoint_store = checkpoint_store
        self.tasks: dict[str, Task] = {}

    def _load_state(
        self,
        task: Task
    ) -> TaskExecutionState:

        if self.checkpoint_store is None:

            return TaskExecutionState(
                task_id=task.id
            )

        state = self.checkpoint_store.load(task.id)

        if state is None:

            return TaskExecutionState(task_id=task.id)

        return state

    def create_task(
        self,
        proposal: TaskProposal
    ) -> Task:

        agent_name = proposal.assigned_agent

        if not self.agent_registry.has(agent_name):
            raise ValueError(f"Unknown agent: {agent_name}")

        task = self.task_factory.create_from_proposal(proposal)

        if task.id in self.tasks:
            raise ValueError(f"Task '{task.id}' already exists.")

        self.tasks[task.id] = task

        return task

    async def run_task(
        self,
        task: Task,
        context: dict | None = None
    ) -> AgentResult:

        if task.assigned_agent is None:

            raise ValueError(f"Task '{task.id}' has no assigned agent.")

        agent = self.agent_registry.get(task.assigned_agent)

        state = self._load_state(task)

        task.status = "running"

        result = await agent.run(
            task=task,
            context=context,
            state=state
        )

        task.result = result

        if result.success:

            task.status = "completed"
            task.error = None

        else:

            task.status = "failed"
            task.error = result.error

        return result

    async def run_proposal(
        self,
        proposal: TaskProposal,
        context: dict | None = None
    ) -> AgentResult:

        task = self.create_task(
            proposal
        )

        return await self.run_task(
            task=task,
            context=context
        )

    async def run_proposals(
        self,
        proposals: list[TaskProposal],
        context: dict | None = None
    ) -> list[AgentResult]:

        results: list[AgentResult] = []

        for proposal in proposals:

            result = await self.run_proposal(
                    proposal=proposal,
                    context=context
            )
        

            results.append(
                result
            )

        return results