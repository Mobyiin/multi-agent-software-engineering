import inspect
import json
import os

from typing import Any

from openai import AsyncOpenAI, RateLimitError

from pydantic import TypeAdapter
from llm.base_model_client import BaseModelClient

from llm.error_utils import (
    extract_retry_after,
    is_daily_quota_error,
    is_rate_limit_error,
    is_transient_network_error,
    is_transient_server_error,
)

from models.model_response import ModelResponse

from models.quota_exhausted_error import QuotaExhaustedError


from models.rate_limit_error import  RateLimitError


from models.transient_model_error import TransientModelError


class OpenAICompatibleModelClient(BaseModelClient):
    def __init__(
        self,
        model: str,
        api_key_env: str,
        base_url: str,
        label: str,
        rate_limit_manager=None,
    ):
        api_key = os.getenv(
            api_key_env
        )

        if not api_key:

            raise RuntimeError(
                f"{api_key_env} "
                "is not configured."
            )

        self.model = model

        self.label = label

        self.rate_limit_manager = (
            rate_limit_manager
        )

        self.rate_limit_key = (
            f"{label}:{model}"
        )

        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def generate(self,messages: list[dict],tools: dict | None = None) -> ModelResponse:

        if self.rate_limit_manager is not None:
            await (self.rate_limit_manager.acquire(self.rate_limit_key))

        converted_messages = (
            self._convert_messages(messages)
        )

        converted_tools = (
            self._convert_tools(tools or {})
        )

        kwargs: dict[str,Any] = {
            "model": self.model,
            "messages": (
                converted_messages
            )
        }

        if converted_tools:
            kwargs["tools"] = (converted_tools)
            kwargs["tool_choice"] = "auto"

        try:
            response = (
                await self.client.chat.completions.create(**kwargs)
            )

        except Exception as error:

            if is_daily_quota_error(error):

                retry_after = (
                    extract_retry_after(error,default=3600.0)
                )

                raise (
                    QuotaExhaustedError(
                        retry_after=(retry_after),
                        key=(self.rate_limit_key),
                        message=str(error)
                    )
                ) from error

            if is_rate_limit_error(error):

                retry_after = (extract_retry_after(error,default=60.0))

                raise RateLimitError(
                    retry_after=(retry_after),
                    key=(self.rate_limit_key),
                    message=str(error)
                ) from error

            if (
                is_transient_network_error(error)
                or
                is_transient_server_error(error)
            ):

                raise (
                    TransientModelError(
                        retry_after=5.0,
                        key=(self.rate_limit_key),
                        message=str(error)
                    )
                ) from error

            raise

        if not response.choices:

            raise RuntimeError (
                f"{self.label} "
                "returned no choices.")

        message = response.choices[0].message


        tool_calls = (message.tool_calls or [])

        if tool_calls:
            tool_call = tool_calls[0]

            function_call = tool_call.function

            try:

                arguments = json.loads(
                    function_call.arguments
                    or "{}"
                )

            except (json.JSONDecodeError,TypeError):

                arguments = {}

            return ModelResponse(
                tool_name = function_call.name ,
                tool_arguments = arguments ,
                tool_call_id = tool_call.id ,
                is_final=False
            )

        raw_content = (message.content or "")

        if isinstance(raw_content,str):

            content = (raw_content.strip())

        else:

            content = str(raw_content).strip()

        if content.startswith("FINAL:"):

            final_content = (
                content.removeprefix("FINAL:").strip()
            )

            return ModelResponse(
                content=(final_content),
                is_final=True
            )

        return ModelResponse(
            content=content,
            is_final=False
        )

    def _convert_messages(self,messages: list[dict]) -> list[dict]:

        converted: list[dict] = []

        for message in messages:

            role = message.get("role")
            content = message.get("content","")

            if role in ("system","user","assistant"):
                converted.append(
                    {
                        "role": role,
                        "content": str(
                            content
                        )
                    }
                )
                continue

            if role == "tool":

                tool_name = (message.get("tool_name","unknown_tool"))
                tool_call_id = (message.get("tool_call_id","unknown"))

                converted.append(
                    {
                        "role": "user",
                        "content": (
                            "TOOL RESULT\n"
                            f"Tool: "
                            f"{tool_name}\n"
                            f"Call ID: "
                            f"{tool_call_id}\n"
                            "Result:\n"
                            f"{content}"
                        )
                    }
                )

        return converted

    def _convert_tools(self,tools: dict) -> list[dict]:

        converted: list[dict] = []

        for (name,function) in tools.items():

            signature = (
                inspect.signature(function)
            )
            try:

                type_hints = (inspect.get_annotations(function,eval_str=True)
                )

            except Exception:

                type_hints = {}

            properties = {}
            required = []

            for (parameter_name,parameter) in (signature.parameters.items()):
                annotation = (type_hints.get(parameter_name,str))

                try:

                    parameter_schema = (
                        TypeAdapter(annotation).json_schema()
                    )

                except Exception:
                    parameter_schema = {"type": "string"}

                properties[parameter_name] = (parameter_schema)

                if (parameter.default is inspect.Parameter.empty):
                    required.append(parameter_name)

            parameters = {
                "type": "object",
                "properties": (properties),
                "additionalProperties": False
            }

            if required:

                parameters["required"] = required

            description = (
                inspect.getdoc(function)
                or
                f"Execute {name}."
            )

            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters
                    }
                }
            )

        return converted

    def reset(self) -> None:
        
        pass

    async def close(self) -> None:
        await self.client.close()