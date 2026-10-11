"""Main desktop window for OmniConvert."""

import logging
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QStatusBar, QMessageBox, QButtonGroup
)

from omniconvert.config.settings import AppSettings
from omniconvert.config.paths import get_icon_path
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.core.job_manager import JobManager
from omniconvert.core.history import HistoryManager
from omniconvert.models.conversion_job import ConversionJob
from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.ui.theme import get_theme_stylesheet
from omniconvert.ui.home_view import HomeView
from omniconvert.ui.conversion_workspace import ConversionWorkspaceView
from omniconvert.ui.queue_view import QueueManagerView
from omniconvert.ui.views import (
    HistoryView, FormatExplorerView, SettingsView
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings = None):
        super().__init__()
        self.settings = settings or AppSettings.load()
        self.registry = CapabilityRegistry()
        self.job_manager = JobManager(max_concurrent=self.settings.max_concurrent_jobs)
        self.history_manager = HistoryManager(max_records=self.settings.history_limit)

        self.setWindowTitle("OmniConvert — Universal File Workspace")
        self.resize(1100, 740)
        self.setMinimumSize(880, 580)

        icon_path = get_icon_path(prefer_ico=True)
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._apply_theme()
        self._init_ui()
        self._connect_job_events()
        self._check_system_dependencies()

    @property
    def active_jobs_count(self) -> int:
        return self.job_manager.active_jobs_count()

    def _apply_theme(self):
        qss = get_theme_stylesheet(self.settings.theme)
        self.setStyleSheet(qss)

    def _toggle_theme(self):
        new_theme = "light" if self.settings.theme == "dark" else "dark"
        self.settings.theme = new_theme
        self.settings.save()
        self._apply_theme()
        logger.info("Theme toggled to %s", new_theme)

    def _on_settings_updated(self, updated: AppSettings):
        self.settings = updated
        self.job_manager.thread_pool.setMaxThreadCount(updated.max_concurrent_jobs)
        self.history_manager.max_records = updated.history_limit
        if updated.default_output_dir and not self.conversion_view.output_dir_edit.text().strip():
            self.conversion_view.output_dir_edit.setText(updated.default_output_dir)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(225)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(6)

        # App Brand Header with Custom Icon
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(4, 0, 4, 12)
        icon_png = get_icon_path(prefer_ico=False)
        if icon_png.exists():
            icon_lbl = QLabel()
            pix = QPixmap(str(icon_png)).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
            icon_lbl.setStyleSheet("background: transparent;")
            brand_row.addWidget(icon_lbl)

        brand_label = QLabel("OmniConvert")
        brand_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; background: transparent;")
        brand_row.addWidget(brand_label)
        brand_row.addStretch()
        sidebar_layout.addLayout(brand_row)

        # Nav Buttons
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.nav_btns = {}
        pages = [
            ("Home", 0, "🏠  Home"),
            ("Conversion", 1, "⚡  Workspace"),
            ("Queue", 2, "⏳  Job Queue"),
            ("History", 3, "📜  History"),
            ("Explorer", 4, "🧭  Formats"),
            ("Settings", 5, "⚙️  Settings"),
        ]

        for key, idx, text in pages:
            btn = QPushButton(text)
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            self.nav_group.addButton(btn, idx)
            self.nav_btns[key] = btn
            sidebar_layout.addWidget(btn)

        self.nav_group.idClicked.connect(self._on_nav_clicked)

        sidebar_layout.addStretch()

        # Engine quick status in sidebar footer
        self.engine_status_label = QLabel("Engines: Checking...")
        self.engine_status_label.setWordWrap(True)
        self.engine_status_label.setStyleSheet("font-size: 11px; color: #8a8f98; padding: 4px; background: transparent;")
        sidebar_layout.addWidget(self.engine_status_label)

        root_layout.addWidget(sidebar)

        # 2. Main Stacked Content View
        self.stack = QStackedWidget()

        self.home_view = HomeView()
        self.conversion_view = ConversionWorkspaceView(
            registry=self.registry,
            default_output_dir=self.settings.default_output_dir
        )
        self.queue_view = QueueManagerView(job_manager=self.job_manager)
        self.history_view = HistoryView(history_manager=self.history_manager)
        self.explorer_view = FormatExplorerView(registry=self.registry)
        self.settings_view = SettingsView(
            settings=self.settings,
            on_theme_toggle=self._toggle_theme,
            on_settings_changed=self._on_settings_updated
        )

        # Connect signals
        self.home_view.open_conversion.connect(self._on_files_received)
        self.conversion_view.job_requested.connect(self._on_job_requested)
        self.queue_view.retry_requested.connect(self._on_job_requested)
        self.history_view.retry_requested.connect(self._on_job_requested)

        self.stack.addWidget(self.home_view)        # 0
        self.stack.addWidget(self.conversion_view)  # 1
        self.stack.addWidget(self.queue_view)       # 2
        self.stack.addWidget(self.history_view)     # 3
        self.stack.addWidget(self.explorer_view)    # 4
        self.stack.addWidget(self.settings_view)    # 5

        root_layout.addWidget(self.stack)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("OmniConvert Ready — 100% Local Offline Processing")

    def _connect_job_events(self):
        self.job_manager.signals.completed.connect(self._on_job_completed)
        self.job_manager.signals.failed.connect(self._on_job_failed)

    def _on_nav_clicked(self, page_id: int):
        if page_id == 3:
            self.history_view.refresh()
        self.stack.setCurrentIndex(page_id)

    def _on_files_received(self, files: list):
        self.conversion_view.add_files(files)
        self.nav_btns["Conversion"].setChecked(True)
        self.stack.setCurrentIndex(1)
        self.status_bar.showMessage(f"Loaded {len(files)} file(s) into workspace", 5000)

    def _on_job_requested(self, req: dict):
        dest_dir = req.get("destination_path")
        if not dest_dir and self.settings.default_output_dir:
            dest_dir = Path(self.settings.default_output_dir)

        job = ConversionJob(
            source_path=Path(req["source_path"]),
            target_format=req["target_format"],
            operation_id=req["operation_id"],
            engine=req["engine"],
            settings=req.get("settings") or {},
            destination_path=dest_dir
        )
        self.queue_view.add_job_card(job)
        self.job_manager.submit_job(job, collision_policy=self.settings.collision_policy)
        # Switch to Queue View
        self.nav_btns["Queue"].setChecked(True)
        self.stack.setCurrentIndex(2)
        self.status_bar.showMessage(f"Job queued: {job.source_path.name} ➔ .{job.target_format}")

    def _on_job_completed(self, job_id: str, dest_path: str):
        self.status_bar.showMessage(f"Conversion completed: {dest_path}", 6000)
        job = self.job_manager.get_job(job_id)
        if job and self.settings.save_history:
            self.history_manager.add_job(job)
            self.history_view.refresh()

    def _on_job_failed(self, job_id: str, err):
        self.status_bar.showMessage(f"Job failed: {err.message}", 6000)
        job = self.job_manager.get_job(job_id)
        if job and self.settings.save_history:
            self.history_manager.add_job(job)
            self.history_view.refresh()

    def _check_system_dependencies(self):
        has_ffmpeg = FFmpegDetector().detect().is_available
        has_office = self.registry.is_engine_available("libreoffice")
        ff_str = "Ready" if has_ffmpeg else "Missing"
        off_str = "Ready" if has_office else "Missing"
        self.engine_status_label.setText(f"FFmpeg: {ff_str} | PDF/Word: {off_str}\nImage/Data/Archive/TTS: Ready")

    def closeEvent(self, event):
        """Ensure safe shutdown when background jobs might be active."""
        active = self.job_manager.active_jobs_count()
        if active > 0:
            res = QMessageBox.question(
                self,
                "Confirm Exit",
                f"There are {active} background conversion job(s) in progress.\nAre you sure you want to cancel and exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if res != QMessageBox.Yes:
                event.ignore()
                return
        logger.info("Application closing safely.")
        event.accept()
