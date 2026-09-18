import asyncio
import inspect

from typing import Any, get_type_hints

from google import genai

from llm.base_model_client import BaseModelClient

from llm.error_utils import (
    extract_retry_after,
    is_daily_quota_error,
    is_rate_limit_error,
    is_transient_network_error,
    is_transient_server_error,
    seconds_until_gemini_quota_reset
)

from models.model_response import ModelResponse
from models.quota_exhausted_error import QuotaExhaustedError
from models.rate_limit_error import RateLimitError
from models.transient_model_error import TransientModelError


class GeminiModelClient(BaseModelClient):

    def __init__(
    self,
    model: str,
    api_key: str,
    rate_limit_manager=None,
    label: str | None = None,
    ):
        self.model = model
        self.label = (label or model)
        self.client = genai.Client(api_key=api_key)
        self.rate_limit_manager = (rate_limit_manager)
        self.rate_limit_key = (f"gemini:{label or model}")
        self.previous_interaction_id: (str | None) = None


    async def generate(self,messages: list[dict],tools: dict | None = None) -> ModelResponse:

        gemini_tools = (
            self._convert_tools(tools or {})
        )

        interaction_input = (
            self._build_input(messages)
        )

        interaction = (
            await self._create_interaction
            (
                model=self.model,
                input=interaction_input,
                tools=gemini_tools,
                previous_interaction_id=self.previous_interaction_id
            )
        )


        interaction_id = getattr(interaction,"id",None)

        if interaction_id:
            self.previous_interaction_id = str(interaction_id)

        steps = getattr(interaction,"steps",None) or []

        for step in steps:

            step_type = getattr(step,"type",None)

            if (step_type != "function_call"):
                continue

            tool_name = getattr(step,"name",None)
            tool_call_id = getattr(step,"id",None)
            tool_arguments = getattr(step,"arguments",None) or {}

            if not tool_name:

                return ModelResponse(
                    content=("Model returned a function call without a tool name."),
                    is_final=False
                )

            if not tool_call_id:

                return ModelResponse(
                    content=("Model returned a function call without a call ID."),
                    is_final=False
                )

            return ModelResponse(
                tool_name=tool_name,
                tool_arguments=dict(tool_arguments),
                tool_call_id=str(tool_call_id),
                is_final=False
            )


        content = (getattr(interaction,"output_text",None) or "").strip()

        if content.startswith("FINAL:"):

            return ModelResponse (
                content=(content.removeprefix("FINAL:").strip()),
                is_final=True
            )

        return ModelResponse(
            content=content,
            is_final=False
        )


    async def _create_interaction(self,**kwargs):

        if (self.rate_limit_manager is not None):

            await (self.rate_limit_manager.acquire(self.rate_limit_key))

        try:

            return await asyncio.to_thread(self.client.interactions.create,**kwargs)

        except Exception as error:

            if is_daily_quota_error(error):
                retry_after = (seconds_until_gemini_quota_reset())
                raise QuotaExhaustedError(
                    retry_after=
                    retry_after,
                    key=self.rate_limit_key,
                    message=str(error)
                ) from error

            if is_rate_limit_error(error):
                retry_after = (extract_retry_after(error,default=60.0))

                raise RateLimitError(
                    retry_after=
                    retry_after,
                    key=self.rate_limit_key,
                    message=str(error)
                ) from error

            if (is_transient_server_error(error)):
                raise TransientModelError(
                    retry_after=5.0,
                    key=self.rate_limit_key,
                    message=str(error)
                ) from error

            if (is_transient_network_error(error)):
                raise TransientModelError(
                    retry_after=5.0,
                    key=self.rate_limit_key,
                    message=str(error)
                ) from error

            raise


    def _build_input(self,messages: list[dict]) -> Any:

        if not messages:
            raise ValueError(
                "Messages cannot be empty."
            )

        if (self.previous_interaction_id is None):

            parts: list[str] = []

            for message in messages:

                role = message.get("role")
                content = message.get("content","")

                if role == "system":
                    parts.append(
                        "SYSTEM INSTRUCTIONS:\n"
                        f"{content}"
                    )

                elif role == "user":
                    parts.append(
                        "USER:\n"
                        f"{content}"
                    )

                elif role == "assistant":
                    parts.append(
                        "PREVIOUS ASSISTANT RESPONSE:\n"
                        f"{content}"
                    )

                elif role == "tool":
                    tool_name = (message.get("tool_name","unknown_tool"))
                    call_id = (message.get("call_id","unknown_call"))

                    parts.append(
                        "TOOL RESULT:\n"
                        f"Tool: {tool_name}\n"
                        f"Call ID: {call_id}\n"
                        f"Result:\n"
                        f"{content}"
                    )

            if not parts:

                raise ValueError(
                    "Conversation contains "
                    "no usable messages."
                )

            return "\n\n".join(parts)

        last_message = (messages[-1])

        role = last_message.get("role")

        if role == "tool":
            tool_name = (last_message.get("tool_name"))
            call_id = (last_message.get("call_id"))
            content = (last_message.get("content",""))

            if not tool_name:

                raise ValueError(
                    "Tool result is missing "
                    "tool_name."
                )

            if not call_id:

                raise ValueError(
                    "Tool result is missing "
                    "call_id."
                )

            return [
                {
                    "type": ("function_result"),
                    "name": tool_name,
                    "call_id": call_id,
                    "result": [
                        {
                            "type": "text",
                            "text": str(content)
                        }
                    ]
                }
            ]

        return str(last_message.get("content",""))


    def _convert_tools(self,tools: dict) -> list[dict]:

        converted_tools: (list[dict]) = []

        for (name,function) in tools.items():

            signature = (inspect.signature(function))

            type_hints = (get_type_hints(function))

            properties: dict[str,dict] = {}

            required: list[str] = []

            for (parameter_name,parameter) in (signature.parameters.items()):

                parameter_type = (
                    type_hints.get(parameter_name,str)
                )

                properties[parameter_name] = {
                    "type": (
                        self
                        ._python_type_to_json_type(
                            parameter_type
                        )
                    )
                }

                if (parameter.default is inspect.Parameter.empty):

                    required.append(parameter_name)

            parameters: dict[str,Any] = {
                "type": "object",
                "properties": (properties)
            }

            if required:
                parameters["required"] = required

            converted_tools.append(
                {
                    "type": "function",
                    "name": name,
                    "description": (
                        inspect.getdoc(function)
                        or (
                            f"Execute the "
                            f"{name} tool."
                        )
                    ),
                    "parameters": (parameters)
                }
            )

        return converted_tools

    def _python_type_to_json_type(self,python_type) -> str:
        mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean"
        }
        return mapping.get(python_type,"string")


    def reset(self) -> None:
        self.previous_interaction_id = None