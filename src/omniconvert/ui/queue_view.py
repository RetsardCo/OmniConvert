"""Job Queue UI View displaying real-time background jobs, output folder opening, and retry actions."""

from pathlib import Path
from PySide6.QtCore import Qt, Slot, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QScrollArea
)

from omniconvert.models.conversion_job import ConversionJob, JobState, JobProgress, JobError
from omniconvert.core.job_manager import JobManager


class JobCard(QFrame):
    """Visual card representing a single background conversion job."""

    def __init__(self, job: ConversionJob, on_cancel: callable, on_retry: callable = None, parent=None):
        super().__init__(parent)
        self.job = job
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Header row: file name + state badge + action buttons
        header_row = QHBoxLayout()
        preset = (job.settings or {}).get("quality_preset", "lossless").upper()
        self.title_lbl = QLabel(f"📄 {job.source_path.name} ➔ .{job.target_format.upper()}  [{preset}]")
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent;")
        header_row.addWidget(self.title_lbl)

        header_row.addStretch()

        self.state_lbl = QLabel(job.state.value.capitalize())
        self.state_lbl.setStyleSheet("font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background-color: #3b82f6; color: white;")
        header_row.addWidget(self.state_lbl)

        self.open_btn = QPushButton("Open Folder")
        self.open_btn.setFixedSize(90, 24)
        self.open_btn.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #0284c7; color: white; border: none; border-radius: 4px;")
        self.open_btn.clicked.connect(self._open_output_folder)
        self.open_btn.hide()
        header_row.addWidget(self.open_btn)

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setFixedSize(60, 24)
        self.retry_btn.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #4f46e5; color: white; border: none; border-radius: 4px;")
        self.retry_btn.clicked.connect(self._trigger_retry)
        self.retry_btn.hide()
        header_row.addWidget(self.retry_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(60, 24)
        self.cancel_btn.setStyleSheet("font-size: 11px; padding: 2px 6px; background-color: #dc2626; color: white; border: none; border-radius: 4px;")
        self.cancel_btn.clicked.connect(lambda: self.on_cancel(self.job.id))
        header_row.addWidget(self.cancel_btn)

        layout.addLayout(header_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Detail text
        self.detail_lbl = QLabel(f"Engine: {job.engine} | Queued")
        self.detail_lbl.setStyleSheet("color: #8a8f98; font-size: 11px; background: transparent;")
        self.detail_lbl.setWordWrap(True)
        layout.addWidget(self.detail_lbl)

    def _open_output_folder(self):
        dest = self.job.destination_path
        if dest:
            folder = dest if dest.is_dir() else dest.parent
            if folder.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _trigger_retry(self):
        if self.on_retry:
            self.on_retry(self.job)

    def update_progress(self, progress: JobProgress):
        if progress.percentage is not None:
            self.progress_bar.setValue(int(progress.percentage))
        self.detail_lbl.setText(f"{progress.stage}: {progress.detail}")

    def update_state(self, state: JobState):
        self.state_lbl.setText(state.value.capitalize())
        if state == JobState.COMPLETED:
            self.state_lbl.setStyleSheet("background-color: #16a34a; color: white; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;")
            self.progress_bar.setValue(100)
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.hide()
            self.open_btn.show()
            warn_str = f" | Note: {'; '.join(self.job.warnings)}" if self.job.warnings else ""
            self.detail_lbl.setText(f"Saved to: {self.job.destination_path}{warn_str}")
        elif state == JobState.FAILED:
            self.state_lbl.setStyleSheet("background-color: #dc2626; color: white; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;")
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.hide()
            self.retry_btn.show()
        elif state == JobState.CANCELLED:
            self.state_lbl.setStyleSheet("background-color: #ca8a04; color: white; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px;")
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.hide()
            self.retry_btn.show()


class QueueManagerView(QWidget):
    """Queue dashboard monitoring all conversion tasks in progress and finished."""
    retry_requested = Signal(dict)

    def __init__(self, job_manager: JobManager, parent=None):
        super().__init__(parent)
        self.job_manager = job_manager
        self.cards: dict[str, JobCard] = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title = QLabel("Job Execution Queue")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Active, pending, and completed background conversions.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px;")
        main_layout.addWidget(title)
        main_layout.addWidget(desc)

        # Scroll Area for Job Cards
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignTop)
        self.cards_layout.setSpacing(8)

        self.empty_lbl = QLabel("No conversion jobs running. Start a job in the Workspace view.")
        self.empty_lbl.setStyleSheet("color: #8a8f98; font-style: italic; padding: 20px;")
        self.cards_layout.addWidget(self.empty_lbl)

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll)

    def _connect_signals(self):
        self.job_manager.signals.progress.connect(self._on_job_progress)
        self.job_manager.signals.state_changed.connect(self._on_job_state)
        self.job_manager.signals.failed.connect(self._on_job_failed)

    def add_job_card(self, job: ConversionJob):
        self.empty_lbl.hide()
        card = JobCard(job, on_cancel=self.job_manager.cancel_job, on_retry=self._on_retry_job)
        self.cards[job.id] = card
        self.cards_layout.insertWidget(0, card)

    def _on_retry_job(self, old_job: ConversionJob):
        if old_job.source_path.exists():
            self.retry_requested.emit({
                "source_path": old_job.source_path,
                "operation_id": old_job.operation_id,
                "target_format": old_job.target_format,
                "engine": old_job.engine,
                "settings": dict(old_job.settings or {}),
            })

    @Slot(str, object)
    def _on_job_progress(self, job_id: str, progress: JobProgress):
        if job_id in self.cards:
            self.cards[job_id].update_progress(progress)

    @Slot(str, object)
    def _on_job_state(self, job_id: str, state: JobState):
        if job_id in self.cards:
            self.cards[job_id].update_state(state)

    @Slot(str, object)
    def _on_job_failed(self, job_id: str, error: JobError):
        if job_id in self.cards:
            step_prefix = f"[{error.step}] " if error.step else ""
            self.cards[job_id].detail_lbl.setText(f"Error: {step_prefix}{error.message}")
