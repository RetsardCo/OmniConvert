"""Application paths and environment resolution."""

from pathlib import Path
import os
import sys

def get_app_root() -> Path:
    """Return root directory of the application repository or bundle."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent.parent

def get_app_data_dir() -> Path:
    """Return per-user application storage directory on Windows."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        path = Path(local_app_data) / "OmniConvert"
    else:
        path = Path.home() / ".omniconvert"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_temp_dir() -> Path:
    """Return dedicated temporary directory for scratch files and jobs."""
    path = get_app_data_dir() / "temp"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_logs_dir() -> Path:
    """Return directory for application logs."""
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
