from models.agent_result import AgentResult
from models.manager_plan import TaskProposal

from runtime.orchestrator import Orchestrator
from runtime.repair_planner import RepairPlanner


class ValidationFlow:

    def __init__(
        self,
        orchestrator: Orchestrator,
        repair_planner: RepairPlanner
    ):
        self.orchestrator = orchestrator

        self.repair_planner = repair_planner

    async def run_tests(
        self,
        description: str,
    ) -> AgentResult:

        proposal = TaskProposal(
            description=description,
            assigned_agent="testing_agent",
            complexity="small",
            reason="The staged project must be validated."
        )

        return await self.orchestrator.run_proposal(proposal)
        

    async def validate_until_passed(
        self,
        original_goal: str,
        all_results: list[AgentResult]
    ) -> bool:

        while True:

            result = await self.run_tests(
                    (
                        "Run all relevant automated "
                        "tests for the current staged "
                        "project. Report failures "
                        "precisely."
                    )
                )
    

            all_results.append(result)

            if not result.success:

                return False

            if (result.data.get("test_status") == "passed"):

                return True

            repair_plan = await self.repair_planner.create_repair_plan(
                        original_goal=original_goal,
                        problem_report=result.message
                )
            

            repair_proposals = [
                proposal
                for proposal
                in repair_plan.tasks
                if proposal.assigned_agent
                in {"coding_agent","frontend_agent"}
            ]

            if not repair_proposals:

                return False

            repair_results = await self.orchestrator.run_proposals(repair_proposals)
          

            all_results.extend(repair_results)

            if any(not repair.success for repair in repair_results):

                return False
            
    async def final_validation(
        self,
        original_goal: str,
        all_results: list[AgentResult]
    ) -> bool:

        return await self.validate_until_passed(
                original_goal=original_goal,
                all_results=all_results
            )