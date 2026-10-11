"""Workflow graph models for multi-step cross-category conversions."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
import datetime


@dataclass
class WorkflowStep:
    step_index: int
    capability_id: str
    display_name: str
    engine: str
    input_format: str
    output_format: str
    lossy: bool = False
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowPlan:
    source_format: str
    target_format: str
    steps: List[WorkflowStep] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @property
    def is_multi_step(self) -> bool:
        return len(self.steps) > 1

    @property
    def is_lossy(self) -> bool:
        return any(s.lossy for s in self.steps)

    @property
    def requires_confirmation(self) -> bool:
        return self.is_multi_step or self.is_lossy

    def summary(self) -> str:
        """Return human-readable summary of all steps in the workflow."""
        if not self.steps:
            return "Empty workflow"
        parts = [f"Step {s.step_index}: {s.display_name} (.{s.input_format} ➔ .{s.output_format})" for s in self.steps]
        return "  ➔  ".join(parts)


class WorkflowStepError(RuntimeError):
    """Raised when a specific step in a multi-step workflow fails."""

    def __init__(self, step_index: int, capability_id: str, message: str):
        self.step_index = step_index
        self.capability_id = capability_id
        super().__init__(f"Step {step_index} ({capability_id}) failed: {message}")
