from abc import ABC, abstractmethod

from models.model_response import ModelResponse


class BaseModelClient(ABC):
    @abstractmethod
    async def generate(self,messages: list[dict],tools: dict | None = None) -> ModelResponse:
        pass
