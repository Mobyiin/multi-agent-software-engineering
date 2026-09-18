import json
import os

from pathlib import Path

from dotenv import load_dotenv

from models.model_route import ModelRoute


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parent.parent


ROUTES_FILE = (PROJECT_ROOT / "config" / "model_routes.json")


def load_model_routes(section: str) -> list[ModelRoute]:

    if not ROUTES_FILE.exists():

        raise FileNotFoundError(
            "Model routes file "
            f"not found: {ROUTES_FILE}"
        )

    with open(ROUTES_FILE,"r",encoding="utf-8",) as file:
        data = json.load(file)

    raw_routes = data.get(section)


    if raw_routes is None:

        raise RuntimeError(
            f"Unknown model route "
            f"section: {section}"
        )

    routes: list[ModelRoute] = []

    for raw in raw_routes:

        enabled = raw.get("enabled",True)

        if not enabled:
            continue

        api_key_env = raw["api_key_env"]
        api_key = os.getenv(api_key_env)

        if not api_key:

            print(
                "[ModelRouteLoader] "
                f"Skipping "
                f"{raw['label']}: "
                f"{api_key_env} "
                "is not configured."
            )

            continue

        route = ModelRoute(

            type=raw["type"],
            label=raw["label"],
            api_key_env=(api_key_env),
            model=raw["model"],
            base_url=raw.get("base_url"),
            enabled=True,
            function_calling=raw.get("function_calling",True),
            json_output=raw.get("json_output",True),
            structured_output=raw.get("structured_output",True),
            vision=raw.get("vision",False)
        )

        routes.append(route)

    if not routes:

        raise RuntimeError(
            "No usable model routes "
            f"configured for "
            f"'{section}'."
        )

    return routes