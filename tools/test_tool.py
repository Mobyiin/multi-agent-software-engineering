import subprocess
import sys

from core.paths import STAGING_DIR
from models.process_result import ProcessResult

def run_staged_tests(
    timeout: int = 30,
) -> ProcessResult:
    
    try:
        result = subprocess.run(
            [sys.executable,"-m","pytest","-q"],
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
            stderr=(
                f"Execution timed out after {timeout} seconds."
            ),
            timed_out=True
        )