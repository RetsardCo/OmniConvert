"""Complete UI Views for Conversion History, Format Explorer, and Settings & Dependency Status."""

from pathlib import Path
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QSpinBox, QCheckBox, QFileDialog, QFormLayout, QTextEdit, QMessageBox
)

from omniconvert.config.settings import AppSettings
from omniconvert.core.history import HistoryManager, HistoryRecord
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.engines.office_detector import LibreOfficeDetector
from omniconvert.engines.ocr_engine import TesseractDetector
from omniconvert.engines.speech_engine import SpeechDetector


class HistoryView(QWidget):
    """Interactive conversion history table with folder navigation, retry, and clear controls."""
    retry_requested = Signal(dict)

    def __init__(self, history_manager: HistoryManager = None, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager or HistoryManager()
        self.records: list[HistoryRecord] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Conversion History")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Local audit log of completed and failed conversions (never stores file contents).")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(desc)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self.open_folder_btn = QPushButton("📂 Open Output Folder")
        self.open_folder_btn.clicked.connect(self._open_selected_folder)
        self.retry_btn = QPushButton("🔄 Retry Selected")
        self.retry_btn.clicked.connect(self._retry_selected)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.clicked.connect(self._clear_history)

        header_row.addWidget(self.open_folder_btn)
        header_row.addWidget(self.retry_btn)
        header_row.addWidget(self.refresh_btn)
        header_row.addWidget(self.clear_btn)
        layout.addLayout(header_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Input File", "Operation", "Output", "Engine", "Status", "Duration / Details"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self):
        self.records = self.history_manager.load_records()
        self.table.setRowCount(len(self.records))
        for r_idx, rec in enumerate(self.records):
            detail = f"{rec.duration_seconds:.2f}s"
            if rec.error_summary:
                detail += f" | Error: {rec.error_summary}"
            elif rec.destination_path:
                detail += f" | {rec.destination_path}"

            vals = [
                rec.started_at,
                rec.source_name,
                rec.operation_id,
                f".{rec.target_format.upper()}",
                rec.engine,
                rec.status.upper(),
                detail
            ]
            for c_idx, val in enumerate(vals):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def _on_row_double_clicked(self, row: int, _col: int):
        """Double clicking a history row opens the converted file or its folder."""
        if 0 <= row < len(self.records):
            rec = self.records[row]
            if rec.destination_path:
                dest = Path(rec.destination_path)
                if dest.exists():
                    QDesktopServices.openUrl(QUrl.fromLocalFile(str(dest)))
                    return
            self._open_selected_folder()

    def _open_selected_folder(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.records):
            dest = Path(self.records[row].destination_path)
            if dest.exists():
                folder = dest if dest.is_dir() else dest.parent
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _retry_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.records):
            rec = self.records[row]
            src = Path(rec.source_path)
            if src.exists():
                self.retry_requested.emit({
                    "source_path": src,
                    "operation_id": rec.operation_id,
                    "target_format": rec.target_format,
                    "engine": rec.engine,
                    "settings": {},
                })

    def _clear_history(self):
        if not self.records:
            return
        reply = QMessageBox.question(
            self,
            "Clear History",
            f"Are you sure you want to permanently clear all {len(self.records)} history records?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.history_manager.clear()
            self.refresh()


class FormatExplorerView(QWidget):
    """Searchable Format Explorer and Capability Matrix."""

    def __init__(self, registry: CapabilityRegistry = None, parent=None):
        super().__init__(parent)
        self.registry = registry or CapabilityRegistry()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Format Explorer & Capability Matrix")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Search all supported file formats, conversions, engines, lossiness, and limitations.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        # Filter bar
        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search by extension (e.g. pdf, docx, mp3, flac, png, 7z) or operation...")
        self.search_edit.textChanged.connect(self._populate_table)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["All Categories", "image", "document", "audio", "video", "data", "text", "archive", "binary"])
        self.category_combo.currentIndexChanged.connect(self._populate_table)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["All Statuses", "Available Only", "Unavailable / Optional Missing"])
        self.status_combo.currentIndexChanged.connect(self._populate_table)

        filter_row.addWidget(self.search_edit, stretch=1)
        filter_row.addWidget(self.category_combo)
        filter_row.addWidget(self.status_combo)
        layout.addLayout(filter_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Operation", "Input Formats", "Output", "Engine", "Fidelity", "Status", "Limitations / Notes"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        self._populate_table()

    def _populate_table(self):
        query = self.search_edit.text().strip().lower()
        cat_filter = self.category_combo.currentText().lower()
        status_filter = self.status_combo.currentIndex()

        all_caps = self.registry.get_all(only_available=False)
        filtered = []
        for cap in all_caps:
            avail = self.registry.is_engine_available(cap.engine)
            if status_filter == 1 and not avail:
                continue
            if status_filter == 2 and avail:
                continue
            if cat_filter != "all categories":
                if cat_filter not in [c.lower() for c in cap.input_categories] and cat_filter != cap.output_category.lower():
                    continue
            haystack = f"{cap.id} {cap.display_name} {' '.join(cap.input_formats)} {cap.output_format} {cap.engine} {cap.description}".lower()
            if query and query not in haystack:
                continue
            filtered.append((cap, avail))

        self.table.setRowCount(len(filtered))
        for r_idx, (cap, avail) in enumerate(filtered):
            fidelity = "Lossy (Supports 100% Preset)" if cap.lossy else "Lossless"
            status_txt = "✅ Ready" if avail else f"⚠️ Missing ({cap.engine})"
            notes = "; ".join(cap.limitations) if cap.limitations else cap.description

            row_vals = [
                cap.display_name,
                ", ".join(cap.input_formats[:8]) + ("..." if len(cap.input_formats) > 8 else ""),
                f".{cap.output_format.upper()}",
                cap.engine.upper(),
                fidelity,
                status_txt,
                notes
            ]
            for c_idx, val in enumerate(row_vals):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))


class SettingsView(QWidget):
    """Settings and System Dependency Inspector View."""

    def __init__(self, settings: AppSettings = None, parent=None, on_theme_toggle=None, on_settings_changed=None):
        super().__init__(parent)
        self.settings = settings or AppSettings.load()
        self.on_theme_toggle = on_theme_toggle
        self.on_settings_changed = on_settings_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Settings & System Dependencies")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Configure output directories, collision rules, concurrency, themes, and inspect local engines.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        # Preferences Card
        card = QFrame()
        card.setObjectName("card")
        form = QFormLayout(card)
        form.setSpacing(8)

        # Theme & Log Level
        theme_row = QHBoxLayout()
        self.toggle_theme_btn = QPushButton("Toggle Dark / Light Theme")
        if self.on_theme_toggle:
            self.toggle_theme_btn.clicked.connect(self.on_theme_toggle)
        theme_row.addWidget(self.toggle_theme_btn)
        theme_row.addSpacing(20)
        theme_row.addWidget(QLabel("Log Level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText(self.settings.log_level)
        self.log_level_combo.currentTextChanged.connect(self._save_preferences)
        theme_row.addWidget(self.log_level_combo)
        theme_row.addStretch()
        form.addRow("Appearance & Logging:", theme_row)

        # Default Output Folder
        out_row = QHBoxLayout()
        self.out_dir_edit = QLineEdit(self.settings.default_output_dir)
        self.out_dir_edit.setPlaceholderText("Leave empty to use source file's folder")
        self.out_dir_edit.textChanged.connect(self._save_preferences)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        out_row.addWidget(self.out_dir_edit, stretch=1)
        out_row.addWidget(browse_btn)
        form.addRow("Default Output Folder:", out_row)

        # Temporary Scratch Folder
        temp_row = QHBoxLayout()
        self.temp_dir_edit = QLineEdit(self.settings.temp_dir)
        self.temp_dir_edit.setPlaceholderText("Default: %LOCALAPPDATA%\\OmniConvert\\Temp")
        self.temp_dir_edit.textChanged.connect(self._save_preferences)
        temp_browse_btn = QPushButton("Browse...")
        temp_browse_btn.clicked.connect(self._browse_temp_dir)
        temp_row.addWidget(self.temp_dir_edit, stretch=1)
        temp_row.addWidget(temp_browse_btn)
        form.addRow("Temp Scratch Folder:", temp_row)

        # Collision policy, Concurrency & Archive Bomb Limit
        exec_row = QHBoxLayout()
        self.collision_combo = QComboBox()
        self.collision_combo.addItems(["rename", "overwrite", "ask"])
        self.collision_combo.setCurrentText(self.settings.collision_policy)
        self.collision_combo.currentTextChanged.connect(self._save_preferences)
        exec_row.addWidget(self.collision_combo)
        exec_row.addSpacing(16)
        exec_row.addWidget(QLabel("Max Concurrent Jobs:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 8)
        self.concurrent_spin.setValue(self.settings.max_concurrent_jobs)
        self.concurrent_spin.valueChanged.connect(self._save_preferences)
        exec_row.addWidget(self.concurrent_spin)
        exec_row.addSpacing(16)
        exec_row.addWidget(QLabel("Max Archive Extraction (MB):"))
        self.archive_limit_spin = QSpinBox()
        self.archive_limit_spin.setRange(10, 10240)
        self.archive_limit_spin.setValue(self.settings.max_archive_mb)
        self.archive_limit_spin.valueChanged.connect(self._save_preferences)
        exec_row.addWidget(self.archive_limit_spin)
        exec_row.addStretch()
        form.addRow("Collision & Safety Limits:", exec_row)

        # History settings
        hist_row = QHBoxLayout()
        self.save_history_chk = QCheckBox("Record conversion history locally")
        self.save_history_chk.setChecked(self.settings.save_history)
        self.save_history_chk.toggled.connect(self._save_preferences)
        self.history_limit_spin = QSpinBox()
        self.history_limit_spin.setRange(10, 2000)
        self.history_limit_spin.setValue(self.settings.history_limit)
        self.history_limit_spin.valueChanged.connect(self._save_preferences)
        hist_row.addWidget(self.save_history_chk)
        hist_row.addSpacing(16)
        hist_row.addWidget(QLabel("Max Records:"))
        hist_row.addWidget(self.history_limit_spin)
        hist_row.addStretch()
        form.addRow("History Retention:", hist_row)

        layout.addWidget(card)

        # Dependency & Privacy Status Card
        dep_card = QFrame()
        dep_card.setObjectName("card")
        dep_layout = QVBoxLayout(dep_card)
        dep_title = QLabel("Local Engine & Dependency Status Report")
        dep_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        dep_layout.addWidget(dep_title)

        self.dep_report_text = QTextEdit()
        self.dep_report_text.setReadOnly(True)
        self.dep_report_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px;")
        dep_layout.addWidget(self.dep_report_text)
        layout.addWidget(dep_card)

        self._refresh_dependency_report()

    def _browse_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Default Output Folder")
        if folder:
            self.out_dir_edit.setText(folder)

    def _browse_temp_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Temporary Scratch Folder")
        if folder:
            self.temp_dir_edit.setText(folder)

    def _save_preferences(self):
        self.settings.default_output_dir = self.out_dir_edit.text().strip()
        self.settings.temp_dir = self.temp_dir_edit.text().strip()
        self.settings.collision_policy = self.collision_combo.currentText()  # type: ignore
        self.settings.max_concurrent_jobs = self.concurrent_spin.value()
        self.settings.max_archive_mb = self.archive_limit_spin.value()
        self.settings.log_level = self.log_level_combo.currentText()  # type: ignore
        self.settings.save_history = self.save_history_chk.isChecked()
        self.settings.history_limit = self.history_limit_spin.value()
        self.settings.save()
        if self.on_settings_changed:
            self.on_settings_changed(self.settings)

    def _refresh_dependency_report(self):
        ff_info = FFmpegDetector().detect()
        lo_info = LibreOfficeDetector().detect()
        ocr_info = TesseractDetector().detect()
        sp_info = SpeechDetector().detect()

        lines = [
            "=== Required & Built-In Local Engines ===",
            "✅ Image Engine (Pillow + PyMuPDF SVG): Ready",
            "✅ PDF & Word Engine (pypdf + PyMuPDF + pdf2docx + python-docx + ReportLab): Ready (PDF <-> DOCX, PDF <-> Image/HTML/MD)",
            "✅ Office Spreadsheet & Slide Engine (openpyxl + python-pptx): Ready (XLSX <-> PDF/CSV/JSON, PPTX -> PDF/TXT)",
            "✅ Archive Engine (zipfile + tarfile + gzip + py7zr): Ready (ZIP, TAR, TAR.GZ, GZ, 7Z with Zip-Slip & Bomb Protection)",
            "✅ Structured Data & Static Binary Engine (JSON, YAML, XML, CSV, Strings, SHA-256, PE Headers): Ready",
            f"{'✅' if ff_info.is_available else '⚠️'} Media Engine (FFmpeg / FFprobe): "
            + (f"Ready (v{ff_info.ffmpeg_version} at {ff_info.ffmpeg_path})" if ff_info.is_available else f"Missing ({ff_info.error_message})"),
            f"✅ Local Text-to-Speech (TTS): Ready ({sp_info.tts_engine_name})",
            "",
            "=== Optional External Engines ===",
            f"{'✅' if lo_info.is_available else 'ℹ️'} LibreOffice Headless: "
            + (f"Installed (v{lo_info.version})" if lo_info.is_available else "Not installed (Using built-in Python DOCX/XLSX/PPTX/PDF engine instead)"),
            f"{'✅' if ocr_info.is_available else 'ℹ️'} Local OCR (Tesseract): "
            + (f"Installed ({ocr_info.version}, langs={','.join(ocr_info.languages)})" if ocr_info.is_available else "Not installed (Install via `winget install UB-Mannheim.TesseractOCR`)"),
            f"{'✅' if sp_info.asr_available else 'ℹ️'} Local Speech Recognition (ASR): "
            + ("Installed" if sp_info.asr_available else "Not installed (Optional: `pip install faster-whisper`)"),
            "",
            "=== Privacy & Security Policy ===",
            "🔒 100% Local Processing: All conversions execute strictly on this machine. No files, paths, or telemetry are ever uploaded."
        ]
        self.dep_report_text.setText("\n".join(lines))
