import asyncio

from autogen_agentchat.agents import AssistantAgent

from agent.base_agent import BaseAgent

from llm.error_utils import (
    extract_retry_after,
    is_daily_quota_error,
    is_rate_limit_error,
    is_transient_network_error,
    is_transient_server_error,
    seconds_until_gemini_quota_reset
)

from models.agent_result import AgentResult

from models.manager_plan import ManagerPlan

from models.task import Task


from models.task_execution_state import TaskExecutionState


MANAGER_SYSTEM_PROMPT = """
You are the Manager Agent of a software engineering
multi-agent system.

Your responsibility is planning and delegation only.

You do not modify files and do not execute project tools.

Available implementation workers:
- coding_agent
- frontend_agent

The runtime automatically performs:
- testing
- repair loops
- code review
- documentation
- final validation

Therefore initial plans should primarily contain
implementation tasks for coding_agent or frontend_agent.

Use frontend_agent only when actual frontend/UI work
is required.

Do not create task IDs.
Do not select numeric iteration budgets.

Return a valid structured ManagerPlan.
"""


class ManagerAgent(BaseAgent):

    def __init__(self,model_candidates: list):

        if not model_candidates:

            raise ValueError("ManagerAgent requires at least one model candidate.")

        self.model_candidates = model_candidates

        self.current_index = 0

        super().__init__(
            name="manager_agent",
            model_client=(model_candidates[0].client),
            tools={}
        )

    def _create_agent(self,model_client) -> AssistantAgent:

        return AssistantAgent(
            name="manager_agent",
            model_client=model_client,
            system_message=MANAGER_SYSTEM_PROMPT,
            output_content_type=ManagerPlan
        )


    def _extract_plan(self,run_result) -> ManagerPlan:

        messages = getattr(run_result,"messages",None) or []

        if not messages:

            raise RuntimeError(
                "Manager returned no messages."
            )

        last_message = messages[-1]

        content = getattr(last_message,"content",None)

        if isinstance(content,ManagerPlan):

            return content

        if isinstance(content,dict):

            return (ManagerPlan.model_validate(content))

        model_dump = getattr(content,"model_dump",None)

        if callable(model_dump):
            return ManagerPlan.model_validate(model_dump())

        raise TypeError(
            "Manager did not return "
            "a ManagerPlan."
        )


    async def run(
        self,
        task: Task,
        context: dict | None = None,
        state: TaskExecutionState | None = None,
    ) -> AgentResult:

        request = task.description

        if context:

            request += (
                "\n\nAdditional context:\n"
                f"{context}"
            )

        while True:

            recoverable_waits: list[float] = []

            permanent_errors: list[Exception] = []

            candidate_count = len(self.model_candidates)

            start_index = self.current_index


            for offset in range(candidate_count):

                index = (start_index+ offset) % candidate_count

                candidate = self.model_candidates[index]

                print(
                    "[manager_agent] "
                    f"trying "
                    f"{candidate.label}"
                )

                autogen_agent = self._create_agent(candidate.client)
                

                try:

                    run_result = await autogen_agent.run(task=request)

                    plan = (self._extract_plan(run_result))

                    self.current_index = index

                    print(
                        "[manager_agent] "
                        f"selected "
                        f"{candidate.label}"
                    )

                    return AgentResult(
                        success=True,
                        agent_name=self.name,
                        task_id=task.id,
                        message=plan.goal_summary,
                        data={"plan": plan}
                    )

                except Exception as error:

                    if (is_daily_quota_error(error)):

                        wait_for = seconds_until_gemini_quota_reset()

                        recoverable_waits.append(wait_for)

                        print(
                            "[manager_agent] "
                            f"{candidate.label}: "
                            "daily quota exhausted"
                        )

                        continue

                    if (is_rate_limit_error(error)):

                        wait_for = extract_retry_after(error,default=60.0)

                        recoverable_waits.append(wait_for)

                        print(
                            "[manager_agent] "
                            f"{candidate.label}: "
                            "rate limited"
                        )

                        continue

                    if (
                        is_transient_network_error(error) 
                        or 
                        is_transient_server_error(error)
                    ):

                        recoverable_waits.append(5.0)

                        print(
                            "[manager_agent] "
                            f"{candidate.label}: "
                            "temporary error"
                        )

                        continue

                    permanent_errors.append(error)

                    print(
                        "[manager_agent] "
                        f"{candidate.label}: "
                        "unavailable"
                    )

            if recoverable_waits:

                wait_for = min(recoverable_waits)

                print(
                    "[manager_agent] "
                    "all candidates currently "
                    "unavailable. "
                    f"retrying in "
                    f"{wait_for:.1f}s"
                )

                await asyncio.sleep(wait_for)

                continue

            if permanent_errors:

                error = permanent_errors[-1]

                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    task_id=task.id,
                    message=("Manager is blocked by a permanent error."),
                    error=str(error)
                )

            return AgentResult(
                success=False,
                agent_name=self.name,
                task_id=task.id,
                message=("No Manager model candidate was available.")
            )