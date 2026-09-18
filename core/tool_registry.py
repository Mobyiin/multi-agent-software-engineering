from tools.file_tool import (
    list_files,
    read_file,
    read_staged_file,
    write_staged_file
)

from tools.execution_tool import run_staged_python
from tools.test_tool import run_staged_tests


CODING_TOOLS = {
    "list_files": list_files,
    "read_staged_file": read_staged_file,
    "write_staged_file": write_staged_file,
    "run_staged_python": run_staged_python,
    "run_staged_tests": run_staged_tests
}

TESTING_TOOLS = {
    "list_files": list_files,
    "read_staged_file": read_staged_file,
    "run_staged_tests": run_staged_tests
}

CODE_REVIEW_TOOLS = {
    "list_files": list_files,
    "read_staged_file": read_staged_file,
    "read_file": read_file
}

DOCUMENTATION_TOOLS = {
    "list_files": list_files,
    "read_staged_file": read_staged_file,
    "write_staged_file": write_staged_file
}

FRONTEND_TOOLS = {
    "list_files": list_files,
    "read_staged_file": read_staged_file,
    "write_staged_file": write_staged_file
}