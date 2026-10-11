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

def get_resources_dir() -> Path:
    """Return directory containing application static resources and icons."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        res_dir = Path(getattr(sys, "_MEIPASS")) / "omniconvert" / "resources"
        if res_dir.exists():
            return res_dir
    path = Path(__file__).resolve().parent.parent / "resources"
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_icon_path(prefer_ico: bool = False) -> Path:
    """Return path to the application icon (.png or .ico)."""
    res_dir = get_resources_dir()
    if prefer_ico:
        ico_path = res_dir / "icon.ico"
        if ico_path.exists():
            return ico_path
    png_path = res_dir / "icon.png"
    if png_path.exists():
        return png_path
    return res_dir / "icon.ico"

def get_history_path() -> Path:
    """Return path to the persistent conversion history JSON file."""
    return get_app_data_dir() / "history.json"

