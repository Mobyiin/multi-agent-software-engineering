import os

from dataclasses import dataclass

from typing import Any

from autogen_core.models import ModelInfo

from autogen_ext.models.openai import OpenAIChatCompletionClient


from llm.fallback_model_client import FallbackModelClient

from llm.gemini_model_client import GeminiModelClient


from llm.model_route_loader import load_model_routes

from llm.openai_compatible_model_client import OpenAICompatibleModelClient


@dataclass
class ManagerModelCandidate:
    label: str
    client: Any


def create_worker_model_client(rate_limit_manager) -> FallbackModelClient:

    routes = load_model_routes("workers")
    clients = []

    for route in routes:
        api_key = os.getenv(route.api_key_env)

        if not api_key:
            continue

        if (route.type == "gemini_native"):

            client = (
                GeminiModelClient(
                    model=(route.model),
                    api_key=(api_key),
                    label=(route.label),
                    rate_limit_manager=(rate_limit_manager)
                )
            )

            clients.append(client)

            continue

        if (route.type == "openai_compatible"):

            if not route.base_url:

                raise RuntimeError(
                    f"Route "
                    f"{route.label} "
                    "requires base_url."
                )

            client = (
                OpenAICompatibleModelClient(
                    model=(route.model),
                    api_key_env=(route.api_key_env),
                    base_url=(route.base_url),
                    label=(route.label),
                    rate_limit_manager=(rate_limit_manager)
                )
            )

            clients.append(client)

            continue

        raise RuntimeError(
            "Unknown model "
            f"route type: "
            f"{route.type}"
        )

    if not clients:

        raise RuntimeError("No Worker model clients could be created.")

    return FallbackModelClient(clients=clients)


def create_manager_model_clients() -> list[ManagerModelCandidate]:

    routes = load_model_routes("manager")

    candidates: list[ManagerModelCandidate] = []

    for route in routes:
        api_key = os.getenv(route.api_key_env)
        if not api_key:

            continue

        if (route.type != "openai_compatible"):

            raise RuntimeError(
                "Manager route "
                f"{route.label} "
                "must currently use "
                "openai_compatible."
            )

        if not route.base_url:

            raise RuntimeError(
                f"Manager route "
                f"{route.label} "
                "requires base_url."
            )

        model_info = ModelInfo(
            vision=(route.vision),
            function_calling=(route.function_calling),
            json_output=(route.json_output),
            structured_output=(route.structured_output),
            family="unknown"
        )

        client = (
            OpenAIChatCompletionClient(
                model=(route.model),
                api_key=(api_key),
                base_url=(route.base_url),
                model_info=(model_info)
            )
        )

        candidates.append(
            ManagerModelCandidate(
                label=(route.label),
                client=client
            )
        )

    if not candidates:

        raise RuntimeError("No Manager model candidates configured.")

    return candidates