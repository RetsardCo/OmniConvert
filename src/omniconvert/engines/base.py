"""Abstract base class for all conversion engines."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Callable, Optional

from omniconvert.models.conversion_job import ConversionJob, JobProgress

class BaseEngine(ABC):
    """Base interface for all file processing engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name identifier of the engine (e.g. 'pillow', 'ffmpeg')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the engine dependencies and binaries are ready."""
        pass

    @abstractmethod
    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """
        Execute the conversion job inside the provided isolated workspace.
        Must return the Path of the produced output file inside the workspace.
        """
        pass
