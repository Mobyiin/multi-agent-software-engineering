import asyncio
from collections import defaultdict
from dataclasses import dataclass
from time import monotonic
from typing import Awaitable, Callable


@dataclass
class RateLimitState:
    next_allowed_at: float = 0.0
    retry_count: int = 0


class RateLimitManager:

    def __init__(
        self,
        sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep
    ):
        self.sleep_func = sleep_func
        self._states: dict[str, RateLimitState] = defaultdict(RateLimitState)

    async def acquire(
        self,
        key: str
    ) -> None:
        state = self._states[key]

        now = monotonic()

        wait_for = state.next_allowed_at - now

        if wait_for > 0:
            await self.sleep_func(wait_for)

    async def handle_rate_limit(
        self,
        key: str,
        retry_after: float
    ) -> None:
        state = self._states[key]

        state.retry_count += 1

        state.next_allowed_at = monotonic() + retry_after


        await self.sleep_func(retry_after)

    def reset(
        self,
        key: str
    ) -> None:
        
        state = self._states[key]
        state.retry_count = 0
        state.next_allowed_at = 0.0