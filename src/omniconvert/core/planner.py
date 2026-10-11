"""Cross-Category Workflow Planner and Multi-Step Execution Engine (Phase 9)."""

from collections import deque
from pathlib import Path
import shutil
import logging
from typing import List, Dict, Optional, Callable, Any

from omniconvert.models.capability import Capability
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.models.workflow import WorkflowStep, WorkflowPlan, WorkflowStepError
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.core.validation import validate_output
from omniconvert.engines.base import BaseEngine

logger = logging.getLogger(__name__)


class WorkflowPlanner:
    """
    Finds bounded, cycle-free conversion paths across registered operations
    and executes multi-step workflows with intermediate validation and cleanup.
    """

    def __init__(self, registry: Optional[CapabilityRegistry] = None):
        self.registry = registry or CapabilityRegistry()

    def find_workflows(
        self,
        source_format: str,
        target_format: str,
        only_available: bool = True,
        max_steps: int = 3
    ) -> List[WorkflowPlan]:
        """
        Perform bounded Breadth-First Search (BFS) over registered capabilities
        to discover valid 1-step or multi-step workflows from source_format to target_format.
        Prevents cycles and limits path length to max_steps.
        """
        src = source_format.lower().lstrip(".")
        dst = target_format.lower().lstrip(".")
        if not src or not dst or max_steps < 1:
            return []

        max_steps = min(max_steps, 4)
        capabilities = self.registry.get_all(only_available=only_available)

        # Queue holds tuples: (current_format, list_of_capabilities_taken, visited_formats_set)
        queue = deque([(src, [], {src})])
        plans: List[WorkflowPlan] = []

        while queue:
            curr_fmt, path_caps, visited = queue.popleft()

            if len(path_caps) >= max_steps:
                continue

            for cap in capabilities:
                # Only allow '*' wildcard capabilities on step 0 if source is binary
                if "*" in cap.input_formats and curr_fmt not in cap.input_formats:
                    if len(path_caps) > 0 or curr_fmt not in ("exe", "dll", "sys", "bin"):
                        continue

                if curr_fmt not in [f.lower() for f in cap.input_formats] and "*" not in cap.input_formats:
                    continue

                out_fmt = cap.output_format.lower().lstrip(".")
                if not out_fmt or out_fmt == "dir":
                    continue

                # Do not use archive packaging as an intermediate step unless the target itself is an archive
                if cap.output_category == "archive" and out_fmt != dst:
                    continue

                # Avoid cycles (unless 1-step format normalization like txt -> txt or pdf -> pdf)
                if out_fmt in visited and not (len(path_caps) == 0 and out_fmt == dst):
                    continue

                new_caps = path_caps + [cap]

                if out_fmt == dst:
                    steps = [
                        WorkflowStep(
                            step_index=i + 1,
                            capability_id=c.id,
                            display_name=c.display_name,
                            engine=c.engine,
                            input_format=src if i == 0 else new_caps[i - 1].output_format,
                            output_format=c.output_format,
                            lossy=c.lossy,
                        )
                        for i, c in enumerate(new_caps)
                    ]
                    plans.append(WorkflowPlan(source_format=src, target_format=dst, steps=steps))
                elif len(new_caps) < max_steps:
                    queue.append((out_fmt, new_caps, visited | {out_fmt}))

        # Sort by shortest step count first, then fewest lossy steps
        plans.sort(key=lambda p: (len(p.steps), sum(1 for s in p.steps if s.lossy)))
        return plans

    def find_multi_step_targets_for_format(
        self,
        source_format: str,
        only_available: bool = True,
        max_steps: int = 2
    ) -> List[WorkflowPlan]:
        """
        Return useful 2-step cross-category workflows starting from source_format
        (e.g., DOCX -> TXT -> WAV, PDF -> TXT -> WAV, PNG -> PDF -> DOCX, etc.).
        """
        src = source_format.lower().lstrip(".")
        direct_caps = [
            c for c in self.registry.get_all(only_available=only_available)
            if src in [f.lower() for f in c.input_formats]
        ]
        direct_outputs = {c.output_format.lower() for c in direct_caps}

        candidate_targets = ["wav", "mp3", "pdf", "docx", "json", "csv", "xlsx", "zip", "png"]
        discovered: List[WorkflowPlan] = []
        for target in candidate_targets:
            if target == src or target in direct_outputs:
                continue
            paths = self.find_workflows(src, target, only_available=only_available, max_steps=max_steps)
            if paths:
                discovered.append(paths[0])

        return discovered

    def execute_plan(
        self,
        plan: WorkflowPlan,
        source_path: Path,
        workspace_dir: Path,
        engines: Dict[str, BaseEngine],
        settings: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """
        Execute each step of a WorkflowPlan sequentially in isolated step workspaces,
        validating every intermediate output before proceeding to the next step.
        """
        if not plan.steps:
            raise ValueError("Cannot execute an empty workflow plan.")

        current_input = source_path
        total_steps = len(plan.steps)
        intermediate_dirs: List[Path] = []
        final_output: Optional[Path] = None

        try:
            for idx, step in enumerate(plan.steps):
                if is_cancelled and is_cancelled():
                    raise InterruptedError(f"Workflow cancelled before Step {step.step_index}.")

                engine = engines.get(step.engine)
                if not engine or not engine.is_available():
                    raise WorkflowStepError(
                        step.step_index,
                        step.capability_id,
                        f"Required engine '{step.engine}' is not available."
                    )

                step_dir = workspace_dir / f"step_{step.step_index}"
                step_dir.mkdir(parents=True, exist_ok=True)
                if idx < total_steps - 1:
                    intermediate_dirs.append(step_dir)

                merged_settings = {**(settings or {}), **step.settings}
                step_job = ConversionJob(
                    source_path=current_input,
                    target_format=step.output_format,
                    operation_id=step.capability_id,
                    engine=step.engine,
                    settings=merged_settings
                )

                def step_progress(p: JobProgress, s_idx=idx, s_name=step.display_name):
                    if progress_callback:
                        base_pct = (s_idx / total_steps) * 100.0
                        sub_pct = (p.percentage or 50.0) / total_steps
                        progress_callback(JobProgress(
                            percentage=min(99.0, base_pct + sub_pct),
                            stage=f"Step {s_idx + 1}/{total_steps}: {s_name}",
                            detail=p.detail
                        ))

                try:
                    step_output = engine.execute(
                        job=step_job,
                        workspace_dir=step_dir,
                        progress_callback=step_progress,
                        is_cancelled=is_cancelled
                    )
                except InterruptedError:
                    raise
                except Exception as e:
                    raise WorkflowStepError(step.step_index, step.capability_id, str(e)) from e

                # Validate intermediate or final output before continuing
                valid, err_msg = validate_output(step_output, step.output_format)
                if not valid:
                    raise WorkflowStepError(
                        step.step_index,
                        step.capability_id,
                        f"Intermediate output validation failed: {err_msg}"
                    )

                current_input = step_output
                final_output = step_output

            # Move final output to root of workspace_dir before cleaning intermediate directories
            if final_output and final_output.parent != workspace_dir:
                promoted = workspace_dir / f"{source_path.stem}.{plan.target_format}"
                shutil.move(str(final_output), str(promoted))
                final_output = promoted

            return final_output

        finally:
            # Clean up all intermediate step directories
            for d in intermediate_dirs:
                if d.exists():
                    shutil.rmtree(d, ignore_errors=True)


class WorkflowEngine(BaseEngine):
    """
    Engine executing multi-step WorkflowPlans and composite cross-category workflows
    such as Archive-to-Combined-PDF.
    """

    def __init__(self, engines: Dict[str, BaseEngine], registry: Optional[CapabilityRegistry] = None):
        self._engines = engines
        self.planner = WorkflowPlanner(registry=registry)

    @property
    def name(self) -> str:
        return "workflow"

    def is_available(self) -> bool:
        return True

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        settings = job.settings or {}

        # Special composite workflow: Archive to Combined PDF
        if job.operation_id == "workflow.archive_to_pdf":
            return self._archive_to_combined_pdf(job.source_path, workspace_dir, settings, progress_callback, is_cancelled)

        # Multi-step plan execution
        plan: Optional[WorkflowPlan] = settings.get("workflow_plan")
        if not plan:
            src_ext = job.source_path.suffix.lower().lstrip(".")
            plans = self.planner.find_workflows(src_ext, job.target_format, only_available=True, max_steps=3)
            if not plans:
                raise ValueError(f"No valid workflow route found from .{src_ext} to .{job.target_format}")
            plan = plans[0]

        return self.planner.execute_plan(
            plan=plan,
            source_path=job.source_path,
            workspace_dir=workspace_dir,
            engines=self._engines,
            settings=settings,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled
        )

    def _archive_to_combined_pdf(
        self,
        archive_path: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Extract archive safely and combine all eligible images, PDFs, and documents into one merged PDF."""
        archive_eng = self._engines.get("archive")
        pdf_eng = self._engines.get("pypdf")
        office_eng = self._engines.get("libreoffice")

        if not archive_eng or not pdf_eng:
            raise RuntimeError("Archive and PDF engines are required for Archive-to-PDF workflow.")

        extract_dir = workspace_dir / "extracted_contents"
        archive_eng.extract_safely(archive_path, extract_dir, progress_callback=progress_callback, is_cancelled=is_cancelled)

        pdfs_dir = workspace_dir / "page_pdfs"
        pdfs_dir.mkdir(parents=True, exist_ok=True)
        generated_pdfs: List[Path] = []

        files = sorted([p for p in extract_dir.rglob("*") if p.is_file()])
        for idx, fpath in enumerate(files):
            if is_cancelled and is_cancelled():
                raise InterruptedError("Archive-to-PDF cancelled.")
            ext = fpath.suffix.lower().lstrip(".")
            if ext == "pdf":
                generated_pdfs.append(fpath)
            elif ext in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
                sub_job = ConversionJob(source_path=fpath, target_format="pdf", operation_id="image.to_pdf", engine="pypdf")
                sub_dir = pdfs_dir / f"item_{idx}"
                sub_dir.mkdir(parents=True, exist_ok=True)
                out_p = pdf_eng.execute(sub_job, sub_dir)
                generated_pdfs.append(out_p)
            elif ext in ("docx", "txt", "md", "markdown", "html", "xlsx", "pptx") and office_eng:
                sub_job = ConversionJob(source_path=fpath, target_format="pdf", operation_id="office.to_pdf", engine="libreoffice")
                sub_dir = pdfs_dir / f"item_{idx}"
                sub_dir.mkdir(parents=True, exist_ok=True)
                out_p = office_eng.execute(sub_job, sub_dir)
                generated_pdfs.append(out_p)

        if not generated_pdfs:
            raise ValueError("Archive contained no eligible images, documents, or PDFs to combine.")

        combined_pdf = workspace_dir / f"{archive_path.stem}.pdf"
        pdf_eng.merge_pdfs(generated_pdfs, combined_pdf)
        return combined_pdf
