"""Application settings and user preferences."""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import logging
from typing import Literal

from omniconvert.config.paths import get_app_data_dir

logger = logging.getLogger(__name__)

CollisionPolicy = Literal["ask", "rename", "overwrite"]
ThemeMode = Literal["dark", "light"]

@dataclass
class AppSettings:
    theme: ThemeMode = "dark"
    default_output_dir: str = ""
    collision_policy: CollisionPolicy = "rename"
    max_concurrent_jobs: int = 2
    save_history: bool = True
    history_limit: int = 200

    @classmethod
    def load(cls) -> "AppSettings":
        config_path = get_app_data_dir() / "settings.json"
        if not config_path.exists():
            return cls()
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception as e:
            logger.warning("Could not read settings from %s, using defaults: %s", config_path, e)
            return cls()

    def save(self) -> None:
        config_path = get_app_data_dir() / "settings.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            logger.error("Failed to save settings to %s: %s", config_path, e)
