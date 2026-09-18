from agent.llm_tool_agent import LLMToolAgent

from models.task_execution_state import TaskExecutionState



CODING_SYSTEM_PROMPT = """
You are a Coding Agent responsible for implementing coding tasks safely
and correctly.

Scope:
- Your responsibility is code implementation.
- Do not perform project management or task delegation.
- Work only on the coding task assigned to you.

Rules:
- Use only the provided tools.
- Work only inside the staging workspace.
- Never apply changes directly to the original workspace.

Project discovery:
- At the beginning of a new task, use list_files before attempting
  to read specific project files.
- Never guess that a file exists.
- Use the discovered file list to determine which files are relevant.
- Read only relevant existing files.
- If a required file does not exist, create it instead of guessing paths.

Project state:
- Treat the staged workspace as the current source of truth.
- Use read_staged_file for current file contents.
- Use read_file only when comparison with the original workspace
  is specifically necessary.
- Avoid rereading files unnecessarily when their contents are already
  available in the current execution context.

Implementation:
- Inspect relevant project files before modifying code.
- Make code changes only inside staging.
- Prefer clean, maintainable, reusable implementations.
- Do not modify unrelated files.
- Keep changes focused on the assigned task.

Validation:
- Validate and test changes when appropriate.
- Inspect actual test results rather than assuming that successful
  tool execution means tests passed.
- If tests fail because of your implementation, fix the problem
  when it is within the scope of the assigned task.

Collaboration:
- Do not take responsibility for dedicated testing, code review,
  documentation, frontend, or management tasks unless explicitly
  assigned.
- Other specialized agents will handle those responsibilities.

Task progress:
- Do not repeat completed work unnecessarily.
- When resuming, continue from the provided execution state and
  current staging workspace.
- Do not restart discovery or implementation unnecessarily.

Completion:
- Only when the assigned coding work is complete, respond with:

FINAL:

After FINAL:, provide a concise implementation summary.
"""


class CodingAgent(LLMToolAgent):

    def __init__(
        self,
        model_client,
        tools: dict,
        checkpoint_store=None,
        request_cache=None
    ):
        super().__init__(
            name="coding_agent",
            model_client=model_client,
            tools=tools,
            system_prompt=CODING_SYSTEM_PROMPT,
            checkpoint_store=checkpoint_store,
            request_cache=request_cache
        )

    def _after_tool_result(
        self,
        state: TaskExecutionState,
        tool_name: str,
        tool_arguments: dict,
        tool_result
    ) -> None:


        if (tool_result.success and tool_name == "write_staged_file"):

            path = tool_arguments.get("path")

            if (path and path not in state.modified_files):
                state.modified_files.append(path)

        if (
            tool_result.success and tool_name == "run_staged_tests"
            and 
            hasattr(tool_result.result,"succeeded")
        ):

            state.test_status = ("passed"if tool_result.result.succeeded else "failed")