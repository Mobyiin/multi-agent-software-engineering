import inspect

from time import monotonic

from llm.base_model_client import BaseModelClient

from models.quota_exhausted_error import QuotaExhaustedError

from models.rate_limit_error import RateLimitError

from models.transient_model_error import TransientModelError



class FallbackModelClient(BaseModelClient):

    def __init__(self,clients: list[BaseModelClient]):
        if not clients:
            raise ValueError("FallbackModelClient requires at least one model client.")

        self.clients = clients
        self.current_index = 0
        self._cooldowns: dict[int,float] = {}

    @property
    def current_client(self) -> BaseModelClient:
        return self.clients[self.current_index]

    @property
    def model(self) -> str:
        return getattr(self.current_client,"model","fallback")

    @property
    def label(self) -> str:
        return getattr(self.current_client,"label",self.model)

    @property
    def rate_limit_manager(self):
        return getattr(self.current_client,"rate_limit_manager",None)

    def _ordered_indexes(self) -> list[int]:
        count = len(self.clients)
        start = self.current_index
        return (list(range(start,count)) + list(range(0,start)))

    def _get_label(self,index: int) -> str:
        client = self.clients[index]
        return getattr(client,"label",getattr(client,"model", f"route-{index}"))

    def _set_cooldown(self,index: int,seconds: float) -> None:
        seconds = max(float(seconds),1.0)
        self._cooldowns[index] = ( monotonic() + seconds)

    def _cooldown_remaining(self,index: int) -> float:
        cooldown_until = (self._cooldowns.get(index,0.0))
        return max(cooldown_until - monotonic(),0.0)

    async def generate(self,messages: list[dict],tools: dict | None = None):
        recoverable_errors: list[Exception] = []
        permanent_errors: list[Exception] = []
        cooldown_waits: list[float] = []
        start_index = self.current_index

        for index in (self._ordered_indexes()):
            client = self.clients[index]
            label = self._get_label(index)
            remaining = self._cooldown_remaining(index)

            if remaining > 0:
                cooldown_waits.append(remaining)

                print(
                    "[FallbackModelClient] "
                    f"skipping {label}: "
                    f"cooldown "
                    f"{remaining:.1f}s"
                )
                continue
            print(
                "[FallbackModelClient] "
                f"trying {label}"
            )

            if index != start_index:
                reset = getattr(client,"reset",None)
                if callable(reset):
                    reset()
            try:

                response = await client.generate(messages=messages,tools=tools)
                self.current_index = index
                self._cooldowns.pop(index,None)

                print(
                    "[FallbackModelClient] "
                    f"selected {label}"
                )
                return response

            except (QuotaExhaustedError) as error:
                retry_after = float(error.retry_after)
                self._set_cooldown(index,retry_after)
                cooldown_waits.append(retry_after)
                recoverable_errors.append(error)

                print(
                    "[FallbackModelClient] "
                    f"{label}: "
                    "daily quota exhausted"
                )
                continue

            except (RateLimitError) as error:
                retry_after = float(error.retry_after)
                self._set_cooldown(index,retry_after)
                cooldown_waits.append(retry_after)
                recoverable_errors.append(error)

                print(
                    "[FallbackModelClient] "
                    f"{label}: "
                    "rate limited"
                )
                continue

            except (TransientModelError) as error:
                retry_after = float(error.retry_after)
                self._set_cooldown(index,retry_after)
                cooldown_waits.append(retry_after)
                recoverable_errors.append(error)

                print(
                    "[FallbackModelClient] "
                    f"{label}: "
                    "temporary failure"
                )
                continue

            except Exception as error:
                permanent_errors.append(error)
                print(
                    "[FallbackModelClient] "
                    f"{label}: "
                    "permanent error: "
                    f"{error}"
                )
                continue

        if recoverable_errors:
            def retry_time(error: Exception) -> float:
                value = getattr(error,"retry_after",60.0)

                try:
                    return float(value)

                except (TypeError,ValueError):
                    return 60.0

            best_error = min(recoverable_errors,key=retry_time)

            raise best_error

        if cooldown_waits:
            wait_for = min(cooldown_waits)
            raise RateLimitError(
                retry_after=(wait_for),
                key=("fallback-sequence"),
                message=("All model routes are currently in cooldown.")
            )

        if permanent_errors:
            raise permanent_errors[-1]

        raise RuntimeError("No model route could be executed.")

    def reset(self) -> None:

        self.current_index = 0

        for client in self.clients:
            reset = getattr(client,"reset",None)
            if callable(reset):
                reset()

    async def close(self) -> None:
        for client in self.clients:
            close = getattr(client,"close",None)
            if not callable(close):
                continue
            result = close()
            if inspect.isawaitable(result):
                await result