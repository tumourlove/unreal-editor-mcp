"""Configuration for unreal-editor-mcp."""

import os
from pathlib import Path

UE_PROJECT_PATH = os.environ.get("UE_PROJECT_PATH", "")
UE_EDITOR_PYTHON_PORT = int(os.environ.get("UE_EDITOR_PYTHON_PORT", "6776"))
UE_MULTICAST_GROUP = os.environ.get("UE_MULTICAST_GROUP", "239.0.0.1")
UE_MULTICAST_PORT = int(os.environ.get("UE_MULTICAST_PORT", "6766"))
UE_MULTICAST_BIND = os.environ.get("UE_MULTICAST_BIND", "127.0.0.1")


def _detect_project_name() -> str:
    """Detect project name from .uproject file in UE_PROJECT_PATH."""
    if not UE_PROJECT_PATH:
        return "unknown"
    p = Path(UE_PROJECT_PATH)
    for f in p.iterdir():
        if f.suffix == ".uproject":
            return f.stem
    return p.name


def get_log_path() -> Path:
    """Return the path to the project's live session log file."""
    project_name = _detect_project_name()
    return Path(UE_PROJECT_PATH) / "Saved" / "Logs" / f"{project_name}.log"


def get_crash_dir() -> Path:
    """Return the path to the project's crash report directory."""
    return Path(UE_PROJECT_PATH) / "Saved" / "Crashes"
