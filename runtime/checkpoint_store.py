import json
from dataclasses import asdict
from pathlib import Path

from models.task_execution_state import TaskExecutionState


class CheckpointStore:
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True,exist_ok=True)

    def save(self,state: TaskExecutionState) -> None:
        path = self._get_path(state.task_id)

        data = {
            "task_id": state.task_id,
            "status": state.status,
            "current_iteration": state.current_iteration,
            "last_tool": state.last_tool,
            "modified_files": state.modified_files,
            "test_status": state.test_status,
            "retry_count": state.retry_count
        }

        with path.open("w",encoding="utf-8",) as file:
            json.dump(data,file,indent=2,ensure_ascii=False)

    def load(
        self,
        task_id: str
    ) -> TaskExecutionState | None:
        path = self._get_path(task_id)

        if not path.exists():
            return None

        with path.open("r",encoding="utf-8") as file:
            data = json.load(file)

        return TaskExecutionState(
            task_id=data["task_id"],
            status=data["status"],
            current_iteration=data["current_iteration"],
            last_tool=data.get("last_tool"),
            modified_files=data.get("modified_files",[]),
            test_status=data.get("test_status"),
            retry_count=data.get("retry_count",0)
        )

    def _get_path(
        self,
        task_id: str
    ) -> Path:
        return (
            self.checkpoint_dir
            / f"{task_id}.json"
        )