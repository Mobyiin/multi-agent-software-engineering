from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

WORKSPACE_DIR = (PROJECT_ROOT / "workspace").resolve()
STAGING_DIR = (PROJECT_ROOT / "staging").resolve()
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"