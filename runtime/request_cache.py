import hashlib
import json

from models.model_response import ModelResponse


class RequestCache:

    def __init__(self):
        self._cache: dict[str, ModelResponse] = {}

    def build_key(
        self,
        model: str,
        messages: list[dict],
        tools: dict,
        staging_hash: str
    ) -> str:

        payload = {
            "model": model,
            "messages": messages,
            "tools": sorted(tools.keys()),
            "staging_hash": staging_hash
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            default=str
        )

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self,key: str) -> ModelResponse | None:
        return self._cache.get(key)

    def set(self,key: str,response: ModelResponse,) -> None:
        self._cache[key] = response