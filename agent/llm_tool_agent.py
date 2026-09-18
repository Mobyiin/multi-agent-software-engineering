import asyncio

from typing import Any

from agent.base_agent import BaseAgent

from core.tool_executor import execute_tool

from models.agent_result import AgentResult
from models.quota_exhausted_error import QuotaExhaustedError
from models.rate_limit_error import RateLimitError
from models.task import Task
from models.task_execution_state import TaskExecutionState
from models.transient_model_error import TransientModelError


from tools.file_tool import build_staging_hash


class LLMToolAgent(BaseAgent):

    def __init__(
        self,
        name: str,
        model_client,
        tools: dict,
        system_prompt: str,
        checkpoint_store=None,
        request_cache=None
    ):
        super().__init__(
            name=name,
            model_client=model_client,
            tools=tools
        )

        self.system_prompt = system_prompt
        self.checkpoint_store = checkpoint_store
        self.request_cache = request_cache


    def _after_tool_result(
        self,
        state: TaskExecutionState,
        tool_name: str,
        tool_arguments: dict,
        tool_result
    ) -> None:

        pass

    def _build_result_data(
        self,
        state: TaskExecutionState,
        response
    ) -> dict[str, Any]:

        return {}


    def _save_checkpoint(
        self,
        state: TaskExecutionState
    ) -> None:

        if (self.checkpoint_store is None):
            return

        self.checkpoint_store.save(state)


    def _build_messages(
        self,
        task: Task,
        context: dict | None,
        state: TaskExecutionState
    ) -> list[dict]:

        messages: list[dict] = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": task.description
            }
        ]

        if context:

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Additional context:\n"
                        f"{context}"
                    )
                }
            )

        if (
            state.current_iteration > 0
            or state.modified_files
            or state.completed_steps
        ):

            messages.append(
                {
                    "role": "user",
                    "content": 
                    (
                        "This task is being resumed.\n"
                        "The staged workspace is the "
                        "source of truth.\n"
                        "Do not repeat completed work.\n\n"
                        f"Previous iterations: "
                        f"{state.current_iteration}\n"
                        f"Completed steps: "
                        f"{state.completed_steps}\n"
                        f"Modified files: "
                        f"{state.modified_files}\n"
                        f"Last action: "
                        f"{state.last_action}\n"
                        f"Last tool: "
                        f"{state.last_tool}\n"
                        f"Last result: "
                        f"{state.last_tool_result}\n"
                        f"Test status: "
                        f"{state.test_status}"
                    )
                }
            )

        return messages


    def _build_cache_key(
        self,
        messages: list[dict]
    ) -> str | None:

        if (self.request_cache is None):
            return None

        model = getattr(self.model_client,"model",self.name)

        staging_hash = build_staging_hash()
        

        return (
            self.request_cache.build_key
            (
                model=model,
                messages=messages,
                tools=self.tools,
                staging_hash=staging_hash
            )
        )


    async def _wait_rate_limit(
        self,
        error: RateLimitError,
        state: TaskExecutionState
    ) -> None:

        retry_after = float(getattr(error,"retry_after",60.0))

        key = getattr(error,"key",self.name)

        state.status = "paused_rate_limit"

        state.last_action = "rate_limit_wait"

        state.retry_count += 1

        self._save_checkpoint(state)

        manager = getattr(self.model_client,"rate_limit_manager",None)

        if manager is not None:

            await manager.handle_rate_limit(key=key,retry_after=retry_after)

        else:

            await asyncio.sleep(retry_after)

        state.status = "running"

        self._save_checkpoint(state)

    async def _wait_daily_quota(
        self,
        error: QuotaExhaustedError,
        state: TaskExecutionState
    ) -> None:

        retry_after = float(getattr(error,"retry_after",3600.0))

        state.status = "paused_daily_quota"

        state.last_action = "daily_quota_wait"

        state.retry_count += 1

        self._save_checkpoint(state)

        print(
            f"[{state.task_id}]"
            f"[{self.name}] "
            "daily_quota_exhausted: "
            f"waiting {retry_after:.0f}s"
        )

        await asyncio.sleep(retry_after)

        state.status = "running"

        self._save_checkpoint(state)

    async def _wait_transient(
        self,
        error: TransientModelError,
        state: TaskExecutionState
    ) -> None:

        retry_after = float(
            getattr(error,"retry_after",5.0)
        )

        state.status = "retrying"

        state.last_action = "transient_retry"

        state.retry_count += 1

        self._save_checkpoint(state)

        await asyncio.sleep(retry_after)

        state.status = "running"

        self._save_checkpoint(
            state
        )


    async def run(
        self,
        task: Task,
        context: dict | None = None,
        state: TaskExecutionState | None = None
    ) -> AgentResult:

        if state is None:

            state = TaskExecutionState(task_id=task.id)

        state.status = "running"

        self._save_checkpoint(state)

        reset_model = getattr(self.model_client,"reset",None)

        if callable(reset_model):
            reset_model()

        messages = (
            self._build_messages(task=task,context=context,state=state)
        )

        print(
            f"[{task.id}]"
            f"[{self.name}] "
            f"agent_started: "
            f"{task.description}"
        )

        while True:

            logical_iteration = (state.current_iteration + 1)

            print(
                f"[{task.id}]"
                f"[{self.name}] "
                f"llm_request: "
                f"Iteration "
                f"{logical_iteration}"
            )


            if (
                task.max_iterations
                and 
                logical_iteration > task.max_iterations 
            ):

                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The original iteration "
                            "budget has been exceeded, "
                            "but the task is not complete. "
                            "Reassess progress, avoid "
                            "repeating work, and continue "
                            "until the assigned task is "
                            "actually complete."
                        )
                    }
                )

            cache_key = (
                self._build_cache_key(messages)
            )

            cached_response = None

            if (cache_key is not None and self.request_cache is not None):

                cached_response = self.request_cache.get(cache_key)
                

            if (cached_response is not None and cached_response.is_final):

                state.status = "completed"

                self._save_checkpoint(state)

                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    task_id=task.id,
                    message=(cached_response.content or ""),
                    data=(
                        self._build_result_data(
                            state=state,
                            response=cached_response
                        )
                    )
                )

            try:

                response = await self.model_client.generate(messages=messages,tools=self.tools)
                

            except QuotaExhaustedError as error:

                print(
                    f"[{task.id}]"
                    f"[{self.name}] "
                    "daily_quota_paused"
                )

                await self._wait_daily_quota(error=error,state=state)

                continue

            except RateLimitError as error:

                print(
                    f"[{task.id}]"
                    f"[{self.name}] "
                    "rate_limited"
                )

                await self._wait_rate_limit(error=error,state=state)

                continue

            except TransientModelError as error:

                print(
                    f"[{task.id}]"
                    f"[{self.name}] "
                    f"transient_error: "
                    f"{error}"
                )

                await self._wait_transient(error=error,state=state)

                continue

            except Exception as error:


                state.status = "blocked"

                state.last_action = "permanent_error"

                self._save_checkpoint(state)

                print(
                    f"[{task.id}]"
                    f"[{self.name}] "
                    f"agent_blocked: "
                    f"{error}"
                )

                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    task_id=task.id,
                    message="Task is blocked by a non-recoverable error.",
                    error=str(error)
                )

            state.current_iteration = logical_iteration

            state.retry_count = 0

            self._save_checkpoint(state)


            if response.is_final:

                state.status = "completed"

                state.last_action = "final"

                self._save_checkpoint(state)

                if (cache_key is not None and self.request_cache is not None):
                    
                    self.request_cache.set(cache_key,response)

                print(
                    f"[{task.id}]"
                    f"[{self.name}] "
                    "agent_completed"
                )

                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    task_id=task.id,
                    message=(response.content or ""),
                    data=(
                        self._build_result_data(
                            state=state,
                            response=response
                        )
                    )
                )

            if response.tool_name:

                tool_name = response.tool_name

                tool_arguments = response.tool_arguments or {}

                print(
                    f"[{task.id}]"
                    f"[{self.name}] "
                    f"tool_requested -> "
                    f"{tool_name}"
                )

                state.last_action = "tool_requested"

                state.last_tool = tool_name

                self._save_checkpoint(state)

                tool_result = execute_tool(
                    tools=self.tools,
                    tool_name=tool_name,
                    arguments=tool_arguments
                )

                state.last_tool_result = tool_result


                self._after_tool_result(
                    state=state,
                    tool_name=tool_name,
                    tool_arguments=tool_arguments,
                    tool_result=tool_result
                )

                self._save_checkpoint(state)

                if tool_result.success:

                    tool_content = str(tool_result.result)

                    print(
                        f"[{task.id}]"
                        f"[{self.name}] "
                        f"tool_completed -> "
                        f"{tool_name}"
                    )

                else:

                    tool_content = (
                        "TOOL ERROR:\n"
                        f"{tool_result.error}"
                    )

                    print(
                        f"[{task.id}]"
                        f"[{self.name}] "
                        f"tool_failed -> "
                        f"{tool_name}: "
                        f"{tool_result.error}"
                    )

                messages.append(
                    {
                        "role": "tool",
                        "tool_name":tool_name,
                        "call_id": response.tool_call_id,
                        "content":tool_content
                    }
                )

                continue

            content = (response.content or "").strip()

            if content:

                messages.append(
                    {
                        "role":"assistant",
                        "content":content
                    }
                )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Continue working on "
                        "the assigned task. "
                        "Use tools when necessary. "
                        "Do not stop until the task "
                        "is complete. When complete, "
                        "respond with FINAL:."
                    )
                }
            )