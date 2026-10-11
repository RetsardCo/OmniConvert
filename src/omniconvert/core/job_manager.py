"""Background Job Manager and Execution Queue using PySide6 ThreadPool."""

import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, Callable
import datetime

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

from omniconvert.models.conversion_job import ConversionJob, JobState, JobProgress, JobError, resolve_output_collision
from omniconvert.models.workflow import WorkflowStepError
from omniconvert.core.temp_files import JobWorkspace
from omniconvert.core.validation import validate_output
from omniconvert.core.planner import WorkflowEngine
from omniconvert.engines.base import BaseEngine
from omniconvert.engines.data_engine import DataEngine
from omniconvert.engines.ffmpeg_engine import FFmpegEngine
from omniconvert.engines.image_engine import ImageEngine
from omniconvert.engines.pdf_engine import PDFEngine
from omniconvert.engines.office_engine import OfficeEngine
from omniconvert.engines.archive_engine import ArchiveEngine
from omniconvert.engines.binary_engine import BinaryEngine
from omniconvert.engines.ocr_engine import OCREngine
from omniconvert.engines.speech_engine import TTSEngine, ASREngine

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """Signals for communicating safe worker updates back to the UI thread."""
    started = Signal(str)                          # job_id
    progress = Signal(str, object)                 # job_id, JobProgress
    state_changed = Signal(str, object)            # job_id, JobState
    completed = Signal(str, str)                   # job_id, destination_path
    failed = Signal(str, object)                   # job_id, JobError
    cancelled = Signal(str)                        # job_id


class JobExecutionRunnable(QRunnable):
    """Runnable worker task executed in QThreadPool."""

    def __init__(
        self,
        job: ConversionJob,
        engine: BaseEngine,
        signals: WorkerSignals,
        collision_policy: str = "rename"
    ):
        super().__init__()
        self.job = job
        self.engine = engine
        self.signals = signals
        self.collision_policy = collision_policy
        self._is_cancelled = False
        self.setAutoDelete(False)

    def cancel(self):
        self._is_cancelled = True

    def _safe_emit(self, sig, *args):
        try:
            sig.emit(*args)
        except RuntimeError:
            pass

    def run(self):
        job_id = self.job.id
        self.job.started_at = datetime.datetime.now()
        self.job.state = JobState.RUNNING
        self._safe_emit(self.signals.started, job_id)
        self._safe_emit(self.signals.state_changed, job_id, JobState.RUNNING)

        workspace = JobWorkspace(job_id)
        workspace_dir = workspace.create()

        try:
            # 1. Check for immediate cancellation
            if self._is_cancelled:
                self._handle_cancelled()
                return

            # 2. Execute conversion inside isolated workspace
            def on_progress(p: JobProgress):
                self.job.progress = p
                self._safe_emit(self.signals.progress, job_id, p)

            intermediate_file = self.engine.execute(
                job=self.job,
                workspace_dir=workspace_dir,
                progress_callback=on_progress,
                is_cancelled=lambda: self._is_cancelled
            )

            if self._is_cancelled:
                self._handle_cancelled()
                return

            # 3. Validation Phase
            self.job.state = JobState.VALIDATING
            self._safe_emit(self.signals.state_changed, job_id, JobState.VALIDATING)
            self._safe_emit(self.signals.progress, job_id, JobProgress(stage="Validating output", percentage=95.0))

            valid, err_msg = validate_output(
                target_path=intermediate_file,
                expected_format=self.job.target_format
            )

            if not valid:
                raise ValueError(f"Output validation failed: {err_msg}")

            # 4. Safe Delivery: move to destination folder
            dest_dir = self.job.destination_path or self.job.source_path.parent
            dest_dir.mkdir(parents=True, exist_ok=True)

            if intermediate_file.is_dir() or self.job.target_format == "dir":
                base_folder_name = intermediate_file.name or f"{self.job.source_path.stem}_extracted"
                final_target = dest_dir / base_folder_name
                if final_target.exists():
                    if self.collision_policy == "overwrite":
                        shutil.rmtree(final_target, ignore_errors=True)
                    else:
                        counter = 1
                        while True:
                            candidate = dest_dir / f"{base_folder_name} ({counter})"
                            if not candidate.exists():
                                final_target = candidate
                                break
                            counter += 1
            else:
                final_target = resolve_output_collision(
                    output_dir=dest_dir,
                    stem=self.job.source_path.stem,
                    target_ext=self.job.target_format,
                    policy=self.collision_policy
                )

                # Prevent overwriting source file accidentally
                if final_target.resolve() == self.job.source_path.resolve():
                    final_target = resolve_output_collision(
                        output_dir=dest_dir,
                        stem=f"{self.job.source_path.stem}_converted",
                        target_ext=self.job.target_format,
                        policy="rename"
                    )

            shutil.move(str(intermediate_file), str(final_target))
            self.job.destination_path = final_target
            self.job.finished_at = datetime.datetime.now()
            self.job.state = JobState.COMPLETED
            self._safe_emit(self.signals.state_changed, job_id, JobState.COMPLETED)
            self._safe_emit(self.signals.completed, job_id, str(final_target))

        except InterruptedError:
            self._handle_cancelled()

        except WorkflowStepError as we:
            logger.error("Workflow Job %s failed at step %s: %s", job_id, we.step_index, we)
            self.job.state = JobState.FAILED
            self.job.finished_at = datetime.datetime.now()
            err = JobError(
                code="WORKFLOW_STEP_ERROR",
                message=str(we),
                step=f"Step {we.step_index} ({we.capability_id})"
            )
            self.job.error = err
            self._safe_emit(self.signals.state_changed, job_id, JobState.FAILED)
            self._safe_emit(self.signals.failed, job_id, err)

        except Exception as e:
            logger.error("Job %s execution failed: %s", job_id, e, exc_info=True)
            self.job.state = JobState.FAILED
            self.job.finished_at = datetime.datetime.now()
            err = JobError(code="EXECUTION_ERROR", message=str(e))
            self.job.error = err
            self._safe_emit(self.signals.state_changed, job_id, JobState.FAILED)
            self._safe_emit(self.signals.failed, job_id, err)

        finally:
            # 5. Always clean up temporary workspace
            workspace.cleanup()

    def _handle_cancelled(self):
        self.job.state = JobState.CANCELLED
        self.job.finished_at = datetime.datetime.now()
        self._safe_emit(self.signals.state_changed, self.job.id, JobState.CANCELLED)
        self._safe_emit(self.signals.cancelled, self.job.id)


_ACTIVE_THREAD_POOLS: list[QThreadPool] = []


class JobManager(QObject):
    """Coordinates job queues, thread pool, and engine dispatch."""

    def __init__(self, max_concurrent: int = 2, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.signals = WorkerSignals()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_concurrent)
        _ACTIVE_THREAD_POOLS.append(self.thread_pool)

        self._jobs: Dict[str, ConversionJob] = {}
        self._runnables: Dict[str, JobExecutionRunnable] = {}
        self._engines: Dict[str, BaseEngine] = {}

        # Register core engines
        self.register_engine(DataEngine())
        self.register_engine(ImageEngine())
        self.register_engine(PDFEngine())
        self.register_engine(ArchiveEngine())
        self.register_engine(BinaryEngine())

        office_eng = OfficeEngine()
        if office_eng.is_available():
            self.register_engine(office_eng)

        ffmpeg_eng = FFmpegEngine()
        if ffmpeg_eng.is_available():
            self.register_engine(ffmpeg_eng)

        tts_eng = TTSEngine()
        if tts_eng.is_available():
            self.register_engine(tts_eng)

        ocr_eng = OCREngine()
        if ocr_eng.is_available():
            self.register_engine(ocr_eng)

        asr_eng = ASREngine()
        if asr_eng.is_available():
            self.register_engine(asr_eng)

        # Register composite workflow engine
        self.register_engine(WorkflowEngine(self._engines))

    def register_engine(self, engine: BaseEngine):
        self._engines[engine.name] = engine

    def get_engine(self, name: str) -> Optional[BaseEngine]:
        return self._engines.get(name)

    def get_job(self, job_id: str) -> Optional[ConversionJob]:
        return self._jobs.get(job_id)

    def submit_job(self, job: ConversionJob, collision_policy: str = "rename") -> str:
        """Enqueue and start conversion job in background thread pool."""
        engine = self._engines.get(job.engine)
        if not engine:
            err = JobError(code="NO_ENGINE", message=f"No engine registered for '{job.engine}'")
            job.state = JobState.FAILED
            job.error = err
            self.signals.failed.emit(job.id, err)
            return job.id

        self._jobs[job.id] = job
        runnable = JobExecutionRunnable(
            job=job,
            engine=engine,
            signals=self.signals,
            collision_policy=collision_policy
        )
        self._runnables[job.id] = runnable
        self.thread_pool.start(runnable)
        return job.id

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job."""
        runnable = self._runnables.get(job_id)
        if runnable:
            runnable.cancel()
            return True
        return False

    def active_jobs_count(self) -> int:
        return self.thread_pool.activeThreadCount()
