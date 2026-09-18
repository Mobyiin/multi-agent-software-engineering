from dataclasses import dataclass


@dataclass
class ProcessResult:
    return_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.return_code == 0