from models.agent_result import AgentResult
from models.manager_plan import ManagerPlan, TaskProposal
from models.workflow_result import WorkflowResult

from runtime.orchestrator import Orchestrator
from runtime.repair_planner import RepairPlanner
from runtime.validation_flow import ValidationFlow


class WorkflowRunner:

    def __init__(
        self,
        orchestrator: Orchestrator,
        repair_planner: RepairPlanner,
        validation_flow: ValidationFlow
    ):
        self.orchestrator =  orchestrator

        self.repair_planner = repair_planner

        self.validation_flow = validation_flow

    async def run(
        self,
        original_goal: str,
        initial_plan: ManagerPlan
    ) -> WorkflowResult:

        all_results: list[AgentResult] = []

        proposals = [
            proposal
            for proposal
            in initial_plan.tasks
            if proposal.assigned_agent
            in {"coding_agent","frontend_agent"}
        ]

        if not proposals:

            return WorkflowResult(
                success=False,
                status="blocked_no_implementation",
                results=all_results,
                error="Manager produced no implementation tasks."
            )

        implementation_results = await self.orchestrator.run_proposals(proposals)

        all_results.extend(implementation_results)

        if any(not result.success for result in implementation_results):

            return WorkflowResult(
                success=False,
                status="blocked_implementation",
                results=all_results
            )


        tests_passed = await self.validation_flow.validate_until_passed(
                original_goal=original_goal,
                all_results=all_results
            )


        if not tests_passed:

            return WorkflowResult(
                success=False,
                status="blocked_testing",
                results=all_results
            )


        review_passed = await self._review_until_passed(
                original_goal=original_goal,
                all_results=all_results
            )

        if not review_passed:

            return WorkflowResult(
                success=False,
                status="blocked_review",
                results=all_results
            )


        documentation_result = (await self.orchestrator.run_proposal(
                TaskProposal(
                    description=(
                        "Create or update the "
                        "documentation for the "
                        "final staged project. "
                        "Include setup, usage, "
                        "architecture and all "
                        "important information "
                        "required by the original "
                        "request."
                    ),
                    assigned_agent="documentation_agent",
                    complexity="medium",
                    reason= "The implementation passed tests and review."
                )
            )
        )

        all_results.append(documentation_result)

        if (not documentation_result.success):

            return WorkflowResult(
                success=False,
                status=("blocked_documentation"),
                results=all_results
            )


        final_passed = (
            await self.validation_flow.final_validation(
                original_goal=original_goal,
                all_results=all_results
            )
        )

        if not final_passed:

            return WorkflowResult(
                success=False,
                status=("blocked_final_validation"),
                results=all_results
            )

        return WorkflowResult(
            success=True,
            status=("ready_for_approval"),
            results=all_results
        )

    async def _review_until_passed(
        self,
        original_goal: str,
        all_results: list[AgentResult]) -> bool:

        while True:

            review_result = (
                await self.orchestrator.run_proposal(
                    TaskProposal(
                        description=(
                            "Review the complete "
                            "staged implementation "
                            "for correctness, bugs, "
                            "maintainability, edge "
                            "cases, architecture and "
                            "compliance with the "
                            "original request."
                        ),
                        assigned_agent="code_review_agent",
                        complexity="small",
                        reason="Implementation has passed automated tests."
                    )
                )
            )

            all_results.append(review_result)

            if not review_result.success:

                return False

            review_status = review_result.data.get("review_status")

            if (review_status== "passed"):

                return True

            if (review_status!= "changes_required"):

                return False

            repair_plan = await self.repair_planner.create_repair_plan(
                    original_goal=original_goal,
                    problem_report=review_result.message
                )
            

            repair_proposals = [proposal
                for proposal
                in repair_plan.tasks
                if proposal.assigned_agent
                in {
                    "coding_agent",
                    "frontend_agent"
                }
            ]

            if not repair_proposals:

                return False

            repair_results = await self.orchestrator.run_proposals(repair_proposals)

            all_results.extend(repair_results)

            if any(not result.success for result in repair_results):

                return False

            tests_passed = (
                await self.validation_flow.validate_until_passed
                (
                    original_goal=original_goal,
                    all_results=all_results
                )
            )

            if not tests_passed:

                return False
