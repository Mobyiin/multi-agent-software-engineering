import os

from dotenv import load_dotenv


load_dotenv()


def get_env(name: str) -> str | None:

    value = os.getenv(name)

    if not value:
        return None

    return value


def require_env(name: str) -> str:

    value = get_env(name)

    if value is None:
        raise RuntimeError(f"{name} is not configured.")

    return value