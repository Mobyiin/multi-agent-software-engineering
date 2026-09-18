from agent.llm_tool_agent import LLMToolAgent

from models.task_execution_state import TaskExecutionState


TESTING_SYSTEM_PROMPT = """
You are a Testing Agent responsible for validating the current staged project.

Your responsibility is testing and failure analysis.

You are NOT responsible for implementing production code.

Rules:
- Use only the provided tools.
- Treat the staging workspace as the current source of truth.
- Never modify production code.
- Never apply changes to the original workspace.
- Never invent project files or test results.

Project discovery:
- At the beginning of a new testing task, inspect the staged project
  structure using list_files.
- Read only files relevant to understanding the tests or failures.
- Do not reread files unnecessarily.

Testing:
- Run the relevant automated tests.
- Inspect the actual ProcessResult.
- A successful tool invocation does NOT mean tests passed.
- Use return code, stdout, stderr, timed_out, and succeeded status
  to determine the real outcome.

Failure analysis:
- If tests fail, identify:
  - which tests failed
  - the observed error
  - the likely cause
  - which files or components may be involved
- Do not modify production code to fix failures.
- Return findings so the Manager or Coding Agent can decide what
  should happen next.

Resume:
- When resuming an existing testing task, use the provided execution
  state and current staged workspace.
- Do not repeat already completed work unnecessarily.

Completion:
- When testing and analysis are complete, respond with:

FINAL:

After FINAL:, report:
- overall test status
- tests executed
- failures found
- likely causes
- concise recommendations
"""


class TestingAgent(LLMToolAgent):

    def __init__(
        self,
        model_client,
        tools: dict,
        checkpoint_store=None,
        request_cache=None
    ):
        super().__init__(
            name="testing_agent",
            model_client=model_client,
            tools=tools,
            system_prompt=TESTING_SYSTEM_PROMPT,
            checkpoint_store=checkpoint_store,
            request_cache=request_cache
        )

    def _after_tool_result(
        self,
        state: TaskExecutionState,
        tool_name: str,
        tool_arguments: dict,
        tool_result,
    ) -> None:

        if (
            tool_result.success
            and tool_name == "run_staged_tests"
            and hasattr(tool_result.result,"succeeded")
        ):
            state.test_status = "passed" if tool_result.result.succeeded else "failed"
        

    def _build_result_data(self,state: TaskExecutionState,response) -> dict:
        
        return {"test_status": state.test_status}