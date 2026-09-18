import subprocess
import sys

from core.paths import STAGING_DIR
from models.process_result import ProcessResult


def run_staged_python(path: str,timeout: int = 10) -> ProcessResult:

    file_path = STAGING_DIR / path

    if not file_path.exists():
        raise FileNotFoundError(f"Staged file not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    if file_path.suffix != ".py":
        raise ValueError("Only Python files can be executed.")

    try:
        
        result = subprocess.run(
            [
                sys.executable,
                str(file_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=STAGING_DIR
        )
        return ProcessResult(
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )
    
    except subprocess.TimeoutExpired:
        return ProcessResult(
            return_code=-1,
            stderr=f"Execution timed out after {timeout} seconds.",
            timed_out=True,
        )