import json
from dataclasses import asdict
from pathlib import Path

from observability.events import Event


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "events.jsonl"


class EventLogger:

    def __init__(self) -> None:
        LOG_DIR.mkdir(parents=True,exist_ok=True)

    def emit(self,event: Event) -> None:

        self._print_event(event)
        self._save_event(event)

    def _print_event(self,event: Event) -> None:

        parts = []
        if event.task_id:
            parts.append(f"[{event.task_id}]")

        if event.agent_id:
            parts.append(f"[{event.agent_id}]")

        prefix = "".join(parts)

        message = f"{prefix} {event.event_type}" 

        if event.tool_name:
            message += f" -> {event.tool_name}"

        if event.message:
            message += f": {event.message}"
        

        print(message)

    def _save_event(self,event: Event) -> None:

        with LOG_FILE.open("a",encoding="utf-8") as file:

            json.dump(asdict(event),file,ensure_ascii=False)

            file.write("\n")


event_logger = EventLogger()
