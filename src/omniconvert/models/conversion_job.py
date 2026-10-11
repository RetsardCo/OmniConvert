"""Conversion job definitions, states, errors, and destination collision resolution."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
import datetime

class JobState(Enum):
    QUEUED = "queued"
    INSPECTING = "inspecting"
    WAITING_DEPENDENCY = "waiting_dependency"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class JobError:
    code: str
    message: str
    details: Optional[str] = None
    step: Optional[str] = None

@dataclass
class JobProgress:
    percentage: Optional[float] = None
    stage: str = "Ready"
    detail: str = ""

@dataclass
class ConversionJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_path: Path = field(default_factory=Path)
    target_format: str = ""
    operation_id: str = ""
    engine: str = ""
    settings: Dict[str, Any] = field(default_factory=dict)
    destination_path: Optional[Path] = None
    state: JobState = JobState.QUEUED
    progress: JobProgress = field(default_factory=JobProgress)
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    started_at: Optional[datetime.datetime] = None
    finished_at: Optional[datetime.datetime] = None
    error: Optional[JobError] = None
    warnings: list[str] = field(default_factory=list)

def resolve_output_collision(
    output_dir: Path,
    stem: str,
    target_ext: str,
    policy: str = "rename"
) -> Path:
    """
    Safely resolve target output path avoiding unintended source overwrites
    and handling collisions based on policy ('rename', 'overwrite').
    """
    ext = target_ext if target_ext.startswith(".") else f".{target_ext}"
    base_target = output_dir / f"{stem}{ext}"

    if not base_target.exists() or policy == "overwrite":
        return base_target

    # Rename strategy: stem (1).ext, stem (2).ext, etc.
    counter = 1
    while True:
        candidate = output_dir / f"{stem} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1
