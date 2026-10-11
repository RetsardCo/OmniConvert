"""Temporary workspace management for conversion jobs."""

from pathlib import Path
import shutil
import uuid
import logging
from typing import Optional
from omniconvert.config.paths import get_temp_dir

logger = logging.getLogger(__name__)

class JobWorkspace:
    """Manages an isolated temporary scratch folder for a single conversion job."""

    def __init__(self, job_id: Optional[str] = None):
        self.job_id = job_id or str(uuid.uuid4())[:8]
        self.root_dir = get_temp_dir() / f"job_{self.job_id}"
        self._created = False

    def __enter__(self) -> "JobWorkspace":
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()

    def create(self) -> Path:
        """Create the temporary directory."""
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._created = True
        return self.root_dir

    def get_path(self, filename: str) -> Path:
        """Return a path inside this workspace, ensuring it's confined to the workspace."""
        target = (self.root_dir / filename).resolve()
        if not str(target).startswith(str(self.root_dir.resolve())):
            raise ValueError(f"Path traversal detected: {filename}")
        return target

    def cleanup(self) -> bool:
        """Safely delete the workspace directory and all intermediate files."""
        if self.root_dir.exists():
            try:
                shutil.rmtree(self.root_dir, ignore_errors=True)
                self._created = False
                return True
            except Exception as e:
                logger.warning("Failed to clean up job workspace %s: %s", self.root_dir, e)
                return False
        return True
