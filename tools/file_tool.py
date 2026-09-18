import shutil
import hashlib

from pathlib import Path

from core.paths import WORKSPACE_DIR, STAGING_DIR


def read_file(path: str) -> str:
    file_path = (WORKSPACE_DIR / path).resolve()

    if WORKSPACE_DIR not in file_path.parents and file_path != WORKSPACE_DIR:
        raise ValueError("Access outside workspace is not allowed.")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def read_staged_file(path: str) -> str:
    file_path = (STAGING_DIR / path).resolve()

    if STAGING_DIR not in file_path.parents and file_path != STAGING_DIR:
        raise ValueError("Access outside staging is not allowed.")

    if not file_path.exists():
        raise FileNotFoundError(f"Staged file not found: {path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def write_staged_file(path: str, content: str) -> str:
    file_path = (STAGING_DIR / path).resolve()

    if STAGING_DIR not in file_path.parents:
        raise ValueError("Access outside staging is not allowed.")

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)

    return f"Staged file written successfully: {path}"


def get_or_create_staging_workspace() -> Path:

    if STAGING_DIR.exists():
        if not WORKSPACE_DIR.exists():
            raise RuntimeError("Staging exists but the original workspace is missing.")
        return STAGING_DIR

    WORKSPACE_DIR.mkdir(parents=True,exist_ok=True)

    shutil.copytree(WORKSPACE_DIR,STAGING_DIR)

    return STAGING_DIR


def apply_staging_workspace() -> str:
    if not STAGING_DIR.exists():
        raise FileNotFoundError("Staging workspace does not exist.")

    if WORKSPACE_DIR.exists():
        shutil.rmtree(WORKSPACE_DIR)

    shutil.copytree(STAGING_DIR, WORKSPACE_DIR)

    return "Staging workspace applied successfully."


def list_files() -> list[str]:

    if not STAGING_DIR.exists():
        raise FileNotFoundError("Staging workspace does not exist.")

    ignored_directories = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build"
    }

    files: list[str] = []

    for path in STAGING_DIR.rglob("*"):

        relative_path = path.relative_to(STAGING_DIR)

        if any(part in ignored_directories for part in relative_path.parts):
            continue

        if not path.is_file():
            continue

        files.append(relative_path.as_posix())

    files.sort()

    return files


def build_staging_hash() -> str:

    hasher = hashlib.sha256()

    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build"
    }

    for path in sorted(
        STAGING_DIR.rglob("*")
    ):
        if not path.is_file():
            continue

        relative_path = path.relative_to(STAGING_DIR)

        if any(part in ignored_dirs for part in relative_path.parts):
            continue

        hasher.update(str(relative_path).encode("utf-8"))

        hasher.update(path.read_bytes())

    return hasher.hexdigest()