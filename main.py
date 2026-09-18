import asyncio
import inspect

from agent.code_review_agent import CodeReviewAgent
from agent.coding_agent import CodingAgent
from agent.documentation_agent import DocumentationAgent
from agent.frontend_agent import FrontendAgent
from agent.manager_agent import ManagerAgent
from agent.testing_agent import TestingAgent

from app.chat import ChatSession

from core.paths import CHECKPOINT_DIR

from core.tool_registry import (
    CODE_REVIEW_TOOLS,
    CODING_TOOLS,
    DOCUMENTATION_TOOLS,
    FRONTEND_TOOLS,
    TESTING_TOOLS
)

from llm.model_factory import create_manager_model_clients, create_worker_model_client


from runtime.agent_registry import AgentRegistry
from runtime.checkpoint_store import CheckpointStore
from runtime.orchestrator import Orchestrator
from runtime.rate_limit_manager import RateLimitManager
from runtime.repair_planner import RepairPlanner
from runtime.request_cache import RequestCache
from runtime.task_factory import TaskFactory
from runtime.validation_flow import ValidationFlow
from runtime.workflow_runner import WorkflowRunner

from tools.file_tool import get_or_create_staging_workspace


async def close_client(client) -> None:

    close_method = getattr(client,"close",None)

    if not callable(close_method):
        return

    result = close_method()

    if inspect.isawaitable(result):
        await result


async def main() -> None:
    get_or_create_staging_workspace()

    checkpoint_store = CheckpointStore(CHECKPOINT_DIR)

    request_cache = RequestCache()

    rate_limit_manager = RateLimitManager()

    task_factory = TaskFactory()

    coding_model_client = create_worker_model_client(rate_limit_manager)

    testing_model_client = create_worker_model_client(rate_limit_manager)

    review_model_client = create_worker_model_client(rate_limit_manager)

    documentation_model_client = create_worker_model_client(rate_limit_manager)

    frontend_model_client = create_worker_model_client(rate_limit_manager)

    manager_model_candidates = create_manager_model_clients()


    try:

        coding_agent = CodingAgent(
            model_client=coding_model_client,
            tools=CODING_TOOLS,
            checkpoint_store=checkpoint_store,
            request_cache=request_cache
        )

        testing_agent = TestingAgent(
            model_client=testing_model_client,
            tools=TESTING_TOOLS,
            checkpoint_store=checkpoint_store,
            request_cache=request_cache
        )

        review_agent = CodeReviewAgent(
            model_client=review_model_client,
            tools=CODE_REVIEW_TOOLS,
            checkpoint_store=checkpoint_store,
            request_cache=request_cache
        )

        documentation_agent = DocumentationAgent(
                model_client=documentation_model_client,
                tools=DOCUMENTATION_TOOLS,
                checkpoint_store=checkpoint_store,
                request_cache=request_cache
            )

        frontend_agent = FrontendAgent(
            model_client=frontend_model_client,
            tools=FRONTEND_TOOLS,
            checkpoint_store=checkpoint_store,
            request_cache=request_cache
        )


        manager_agent = ManagerAgent(model_candidates=manager_model_candidates)



        registry = AgentRegistry()

        registry.register(coding_agent)

        registry.register(testing_agent)

        registry.register(review_agent)

        registry.register(documentation_agent)

        registry.register(frontend_agent)

        orchestrator = Orchestrator(
            agent_registry=registry,
            task_factory=task_factory,
            checkpoint_store=checkpoint_store
        )

        repair_planner = RepairPlanner(
            manager_agent=manager_agent,
            task_factory=task_factory
        )

        validation_flow = (
            ValidationFlow(
                orchestrator=orchestrator,
                repair_planner=repair_planner
            )
        )

        workflow_runner = (
            WorkflowRunner(
                orchestrator=orchestrator,
                repair_planner=repair_planner,
                validation_flow=validation_flow
            )
        )


        chat = ChatSession(
            manager_agent=manager_agent,
            workflow_runner=workflow_runner,
            task_factory=task_factory
        )

        await chat.run_cli()

    finally:


        for candidate in (manager_model_candidates):

            await close_client(candidate.client)

        worker_clients = [
            coding_model_client,
            testing_model_client,
            review_model_client,
            documentation_model_client,
            frontend_model_client
        ]

        for client in worker_clients:

            await close_client(client)


if __name__ == "__main__":

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")