"""UI Conversion Workspace View connecting file detector, capability registry, workflow planner, and quality/detail controls."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QComboBox, QTextEdit, QFileDialog,
    QSplitter, QFormLayout, QSpinBox, QCheckBox, QLineEdit,
    QScrollArea, QMessageBox
)

from omniconvert.core.file_detector import inspect_file, FileMetadata
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.core.planner import WorkflowPlanner
from omniconvert.models.capability import Capability
from omniconvert.models.workflow import WorkflowPlan
from omniconvert.engines.media_inspector import MediaInspector
from omniconvert.engines.archive_engine import ArchiveEngine


class ConversionWorkspaceView(QWidget):
    job_requested = Signal(dict)

    def __init__(self, registry: CapabilityRegistry = None, default_output_dir: str = "", parent=None):
        super().__init__(parent)
        self.registry = registry or CapabilityRegistry()
        self.planner = WorkflowPlanner(registry=self.registry)
        self.default_output_dir = default_output_dir
        self.files_meta: list[FileMetadata] = []
        self.current_meta: FileMetadata | None = None
        self.available_ops: list[Capability] = []
        self.available_workflows: list[WorkflowPlan] = []
        self._filtered_items: list[tuple[str, Any]] = []  # ("cap", Capability) or ("workflow", WorkflowPlan)
        self._setting_widgets: Dict[str, QWidget] = {}
        self._media_inspector = MediaInspector()
        self._archive_engine = ArchiveEngine()
        self.setAcceptDrops(True)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # Header
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Conversion Workspace")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        sub_title = QLabel("Inspect files, choose direct or multi-step conversions, and customize quality/detail settings.")
        sub_title.setStyleSheet("color: #8a8f98; font-size: 13px;")
        title_box.addWidget(title)
        title_box.addWidget(sub_title)
        top_bar.addLayout(title_box)

        top_bar.addStretch()

        add_btn = QPushButton("+ Add Files")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self._browse_add_files)

        add_folder_btn = QPushButton("+ Add Folder")
        add_folder_btn.clicked.connect(self._browse_add_folder)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_files_confirmed)

        top_bar.addWidget(add_btn)
        top_bar.addWidget(add_folder_btn)
        top_bar.addWidget(clear_btn)
        main_layout.addLayout(top_bar)

        # Splitter: Left (Files List) | Right (Inspection, Quality/Detail & Operation Selection)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)

        # Left: File List Card
        left_card = QFrame()
        left_card.setObjectName("card")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_title = QLabel("Input Files & Folders")
        left_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(left_title)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.setAcceptDrops(True)
        self.file_list.currentRowChanged.connect(self._on_file_selected)
        left_layout.addWidget(self.file_list)

        file_btns = QHBoxLayout()
        self.remove_file_btn = QPushButton("Remove Selected")
        self.remove_file_btn.setToolTip("Remove highlighted file(s) from workspace (Del or Backspace)")
        self.remove_file_btn.clicked.connect(self.remove_selected_files)
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setToolTip("Clear all files and reset workspace")
        self.clear_all_btn.clicked.connect(self.clear_files_confirmed)
        file_btns.addWidget(self.remove_file_btn)
        file_btns.addWidget(self.clear_all_btn)
        left_layout.addLayout(file_btns)

        # Batch image tools box
        batch_card = QFrame()
        batch_card.setStyleSheet("background: #181d28; border: 1px solid #2b3548; border-radius: 6px;")
        batch_vbox = QVBoxLayout(batch_card)
        batch_vbox.setContentsMargins(10, 8, 10, 8)
        batch_vbox.setSpacing(6)

        batch_title = QLabel("📦 Batch Image Operations")
        batch_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #60a5fa;")
        batch_vbox.addWidget(batch_title)

        batch_row = QHBoxLayout()
        self.combine_pdf_btn = QPushButton("📑 Merge to 1 PDF")
        self.combine_pdf_btn.setToolTip("Combine loaded/selected images into 1 multi-page PDF document")
        self.combine_pdf_btn.clicked.connect(self._combine_images_to_pdf)

        self.combine_gif_btn = QPushButton("🎞️ Merge to 1 GIF")
        self.combine_gif_btn.setToolTip("Combine loaded/selected images into 1 animated GIF")
        self.combine_gif_btn.clicked.connect(self._combine_images_to_gif)

        batch_row.addWidget(self.combine_pdf_btn)
        batch_row.addWidget(self.combine_gif_btn)
        batch_vbox.addLayout(batch_row)
        left_layout.addWidget(batch_card)

        splitter.addWidget(left_card)

        # Right: Details, Operation, Quality Preset & Settings Card
        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        self.details_label = QLabel("Select a file from the list to inspect details.")
        self.details_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        right_layout.addWidget(self.details_label)

        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        self.meta_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px;")
        self.meta_text.setFixedHeight(96)
        right_layout.addWidget(self.meta_text)

        # Operation Search & Selector Row
        op_header_row = QHBoxLayout()
        op_lbl = QLabel("Choose Operation / Target Format:")
        op_lbl.setStyleSheet("font-weight: 600;")
        op_header_row.addWidget(op_lbl)
        op_header_row.addStretch()

        self.op_filter_edit = QLineEdit()
        self.op_filter_edit.setPlaceholderText("🔍 Filter operations (e.g. docx, pdf, mp3, wav)...")
        self.op_filter_edit.setMinimumWidth(180)
        self.op_filter_edit.setMaximumWidth(320)
        self.op_filter_edit.textChanged.connect(self._rebuild_operation_combo)
        op_header_row.addWidget(self.op_filter_edit)
        right_layout.addLayout(op_header_row)

        self.op_combo = QComboBox()
        self.op_combo.currentIndexChanged.connect(self._on_operation_changed)
        right_layout.addWidget(self.op_combo)

        # Global Quality / Detail Level Selector
        quality_row = QHBoxLayout()
        q_lbl = QLabel("🎯 Conversion Quality & Detail Level:")
        q_lbl.setStyleSheet("font-weight: 600; color: #3b82f6;")
        quality_row.addWidget(q_lbl)

        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.setObjectName("qualityPresetCombo")
        self.quality_preset_combo.addItem("💎 Lossless / Exact Quality (100% Detail & Fidelity)", "lossless")
        self.quality_preset_combo.addItem("✨ High Quality (Detailed - 95% / 256 kbps / 300 DPI)", "high")
        self.quality_preset_combo.addItem("⚖️ Balanced (Standard - 85% / 192 kbps / 150 DPI)", "balanced")
        self.quality_preset_combo.addItem("⚡ Compact / Fast (Compressed - 70% / 128 kbps / 96 DPI)", "compact")
        self.quality_preset_combo.addItem("🎛️ Custom (Adjust Fine-Grained Controls Below)", "custom")

        self.quality_preset_combo.setItemData(0, "Lossless / Exact: 100% quality, 4:4:4 lossless chroma, True Lossless WebP/AVIF, 24-bit PCM/ALAC audio, CRF 14 video, 300 DPI document rasterization.", Qt.ToolTipRole)
        self.quality_preset_combo.setItemData(1, "High Quality: 95% quality, 256 kbps audio, CRF 18 visually transparent video, 250 DPI rendering.", Qt.ToolTipRole)
        self.quality_preset_combo.setItemData(2, "Balanced: Standard 85% quality, 192 kbps audio, CRF 23 video, 150 DPI rendering. Excellent size-to-quality balance.", Qt.ToolTipRole)
        self.quality_preset_combo.setItemData(3, "Compact / Fast: 70% quality, 128 kbps audio, CRF 28 video, 96 DPI rendering. Optimized for small file sizes.", Qt.ToolTipRole)
        self.quality_preset_combo.setItemData(4, "Custom: Fully manual configuration using the sliders and inputs below.", Qt.ToolTipRole)
        self.quality_preset_combo.setToolTip("Select global conversion detail and compression fidelity preset.")

        self.quality_preset_combo.currentIndexChanged.connect(self._on_quality_preset_changed)
        quality_row.addWidget(self.quality_preset_combo, stretch=1)
        right_layout.addLayout(quality_row)

        # Dynamic Context-Sensitive Settings Area
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setObjectName("settingsScroll")
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setMinimumHeight(140)
        self.settings_container = QWidget()
        self.settings_container.setObjectName("settingsContainer")
        self.settings_form = QFormLayout(self.settings_container)
        self.settings_form.setContentsMargins(12, 10, 12, 10)
        self.settings_form.setSpacing(8)
        self.settings_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.settings_scroll.setWidget(self.settings_container)
        right_layout.addWidget(self.settings_scroll, stretch=1)

        # Output Folder Selector
        out_row = QHBoxLayout()
        out_lbl = QLabel("Output Folder:")
        out_lbl.setStyleSheet("font-weight: 500;")
        self.output_dir_edit = QLineEdit(self.default_output_dir)
        self.output_dir_edit.setPlaceholderText("Default: Same folder as source file")
        out_browse_btn = QPushButton("Browse...")
        out_browse_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(out_lbl)
        out_row.addWidget(self.output_dir_edit, stretch=1)
        out_row.addWidget(out_browse_btn)
        right_layout.addLayout(out_row)

        # Warning / Limitation / Workflow Step Notice
        self.notice_label = QLabel("")
        self.notice_label.setWordWrap(True)
        self.notice_label.setStyleSheet("color: #d97706; font-size: 12px;")
        right_layout.addWidget(self.notice_label)

        # Action: Convert Selected & Convert All Batch Buttons
        bottom_box = QHBoxLayout()
        self.batch_convert_btn = QPushButton("Convert All Compatible Files")
        self.batch_convert_btn.setEnabled(False)
        self.batch_convert_btn.clicked.connect(self._start_batch_conversion)
        bottom_box.addWidget(self.batch_convert_btn)

        self.burn_iso_btn = QPushButton("💿 Burn to Disc (Windows Disc Burner)")
        self.burn_iso_btn.setStyleSheet("background-color: #854d0e; color: white;")
        self.burn_iso_btn.hide()
        self.burn_iso_btn.clicked.connect(self._launch_windows_iso_burner)
        bottom_box.addWidget(self.burn_iso_btn)

        bottom_box.addStretch()

        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.setObjectName("primaryButton")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_conversion)
        bottom_box.addWidget(self.convert_btn)
        right_layout.addLayout(bottom_box)

        splitter.addWidget(right_card)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter)

    def _browse_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Add")
        if paths:
            self.add_files(paths)

    def _browse_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Package or Inspect")
        if folder:
            self.add_files([folder])

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_dir_edit.setText(folder)

    def add_files(self, paths: list):
        for p in paths:
            meta = inspect_file(p)
            if any(m.path == meta.path for m in self.files_meta):
                continue
            self.files_meta.append(meta)

            if meta.error or not meta.is_readable:
                status_icon = "⚠️"
            elif meta.category == "directory":
                status_icon = "📁"
            else:
                status_icon = "📄"
            item = QListWidgetItem(f"{status_icon} {meta.filename} ({meta.formatted_size}) [{meta.detected_format.upper()}]")
            self.file_list.addItem(item)

        if self.file_list.count() > 0 and self.file_list.currentRow() == -1:
            self.file_list.setCurrentRow(0)

    def clear_files_confirmed(self):
        """Prompt user for confirmation before clearing all workspace files."""
        if not self.files_meta:
            return
        reply = QMessageBox.question(
            self,
            "Clear Workspace",
            f"Are you sure you want to remove all {len(self.files_meta)} file(s) from the workspace?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.clear_files()

    def clear_files(self):
        self.files_meta.clear()
        self.file_list.clear()
        self.current_meta = None
        self.available_ops.clear()
        self.available_workflows.clear()
        self._filtered_items.clear()
        self.details_label.setText("Select a file from the list to inspect details.")
        self.meta_text.clear()
        self.op_combo.clear()
        self._clear_settings_form()
        self.notice_label.setText("")
        self.convert_btn.setEnabled(False)
        self.batch_convert_btn.setEnabled(False)
        self.burn_iso_btn.hide()

    def remove_selected_files(self):
        """Remove currently selected items from the workspace."""
        selected_indexes = sorted(list(set(idx.row() for idx in self.file_list.selectedIndexes())), reverse=True)
        if not selected_indexes:
            current = self.file_list.currentRow()
            if current >= 0:
                selected_indexes = [current]

        for row in selected_indexes:
            if 0 <= row < len(self.files_meta):
                del self.files_meta[row]
                self.file_list.takeItem(row)

        if self.files_meta:
            new_row = min(selected_indexes[-1] if selected_indexes else 0, len(self.files_meta) - 1)
            self.file_list.setCurrentRow(max(0, new_row))
        else:
            self.clear_files()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if file_paths:
            self.add_files(file_paths)
        event.acceptProposedAction()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.file_list.hasFocus():
                self.remove_selected_files()
                return
        super().keyPressEvent(event)

    def _get_target_image_paths(self) -> List[Path]:
        """Collect image files from user selection or all loaded files."""
        selected_rows = sorted(list(set(idx.row() for idx in self.file_list.selectedIndexes())))
        if len(selected_rows) > 1:
            candidate_metas = [self.files_meta[i] for i in selected_rows if 0 <= i < len(self.files_meta)]
        else:
            candidate_metas = self.files_meta

        image_paths = [
            m.path for m in candidate_metas
            if m.category == "image" or m.detected_format.lower() in ("png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "heic", "heif", "gif")
        ]
        return image_paths

    def _combine_images_to_pdf(self):
        """Combine images into a single multi-page PDF."""
        images = self._get_target_image_paths()
        if len(images) < 2:
            self.notice_label.setText("⚠️ Please add at least 2 image files to merge into a multi-page PDF.")
            return

        dest_dir = self._get_destination_dir() or images[0].parent
        settings = self.collect_current_settings()
        settings["batch_image_paths"] = [str(p) for p in images]
        settings["output_filename"] = f"{images[0].stem}_combined.pdf"

        self.job_requested.emit({
            "source_path": images[0],
            "target_format": "pdf",
            "operation_id": "image.batch_to_pdf",
            "engine": "pypdf",
            "settings": settings,
            "destination_path": dest_dir
        })

    def _combine_images_to_gif(self):
        """Combine images into an animated GIF."""
        images = self._get_target_image_paths()
        if len(images) < 2:
            self.notice_label.setText("⚠️ Please add at least 2 image files to merge into an animated GIF.")
            return

        dest_dir = self._get_destination_dir() or images[0].parent
        settings = self.collect_current_settings()
        settings["batch_image_paths"] = [str(p) for p in images]
        settings["output_filename"] = f"{images[0].stem}_animation.gif"
        if "fps" not in settings:
            settings["fps"] = 2
        if "loop" not in settings:
            settings["loop"] = 0

        self.job_requested.emit({
            "source_path": images[0],
            "target_format": "gif",
            "operation_id": "image.batch_to_gif",
            "engine": "pillow",
            "settings": settings,
            "destination_path": dest_dir
        })


    def _inspect_extended_details(self, meta: FileMetadata) -> tuple[List[str], Dict[str, Any]]:
        """Perform deep inspection (dimensions, pages, streams, archive entries) and return extra info lines + flags."""
        extra_lines: List[str] = []
        flags: Dict[str, Any] = {"has_audio": True, "has_subtitles": True}
        if not meta.is_readable or meta.is_empty:
            return extra_lines, flags

        fmt = meta.detected_format.lower()
        try:
            if meta.category == "image" and fmt != "svg":
                from PIL import Image
                with Image.open(meta.path) as img:
                    frames = getattr(img, "n_frames", 1)
                    extra_lines.append(
                        f"Image Details: {img.width}x{img.height} px | Mode: {img.mode} | Frames: {frames}"
                    )
            elif fmt == "pdf":
                import pypdf
                reader = pypdf.PdfReader(str(meta.path))
                enc = "Yes (Password Required)" if reader.is_encrypted else "No"
                pages = len(reader.pages) if not reader.is_encrypted else "?"
                extra_lines.append(f"PDF Details: {pages} page(s) | Encrypted: {enc}")
            elif meta.category in ("audio", "video"):
                if self._media_inspector.ffprobe_path and self._media_inspector.ffprobe_path.exists():
                    info = self._media_inspector.inspect(meta.path)
                    if info.is_valid:
                        flags["has_audio"] = info.has_audio
                        flags["has_subtitles"] = info.has_subtitles
                        parts = [f"Duration: {info.duration_seconds:.2f}s"]
                        if info.video_streams:
                            vs = info.video_streams[0]
                            parts.append(f"Video: {vs.width}x{vs.height} ({vs.codec_name})")
                        if info.audio_streams:
                            aus = info.audio_streams[0]
                            parts.append(f"Audio: {aus.sample_rate}Hz {aus.channels}ch ({aus.codec_name})")
                        else:
                            parts.append("Audio: None")
                        if info.subtitle_streams:
                            parts.append(f"Subtitles: {len(info.subtitle_streams)} track(s)")
                        extra_lines.append("Media Streams: " + " | ".join(parts))
            elif meta.category == "archive":
                manifest = self._archive_engine.inspect_archive(meta.path)
                safety = "Safe" if manifest.is_safe else f"Unsafe ({manifest.safety_error})"
                extra_lines.append(
                    f"Archive Manifest: {manifest.total_files} file(s) | "
                    f"Uncompressed: {manifest.total_uncompressed_bytes:,} bytes | Status: {safety}"
                )
        except Exception:
            pass
        return extra_lines, flags

    def _on_file_selected(self, row: int):
        if row < 0 or row >= len(self.files_meta):
            return
        meta = self.files_meta[row]
        self.current_meta = meta

        self.details_label.setText(f"Inspecting: {meta.filename}")
        info_lines = [
            f"Path: {meta.path}",
            f"Size: {meta.formatted_size} ({meta.size_bytes:,} bytes) | Detected: {meta.detected_format.upper()} ({meta.category.capitalize()})",
            f"MIME: {meta.detected_mime} | Readable: {'Yes' if meta.is_readable else 'No'}",
        ]
        extra_lines, stream_flags = self._inspect_extended_details(meta)
        info_lines.extend(extra_lines)
        if meta.error:
            info_lines.append(f"Error: {meta.error}")
        self.meta_text.setText("\n".join(info_lines))

        ops = self.registry.find_operations_for_file(meta, only_available=True)
        # Filter out stream-dependent operations when the media file lacks those streams
        filtered_ops: List[Capability] = []
        for op in ops:
            if op.id == "video.extract_subtitles" and not stream_flags.get("has_subtitles", True):
                continue
            if op.id.startswith("video.extract_") and op.id != "video.extract_subtitles" and not stream_flags.get("has_audio", True):
                continue
            filtered_ops.append(op)

        self.available_ops = filtered_ops
        self.available_workflows = (
            self.planner.find_multi_step_targets_for_format(meta.detected_format, only_available=True)
            if meta.is_readable and not meta.is_empty
            else []
        )
        if meta and meta.detected_format == "iso":
            self.burn_iso_btn.show()
        else:
            self.burn_iso_btn.hide()
        self._rebuild_operation_combo()

    def _launch_windows_iso_burner(self):
        if not self.current_meta or not self.current_meta.path.exists():
            return
        import subprocess, shutil
        iso_burn_exe = shutil.which("isoburn.exe") or "C:\\Windows\\System32\\isoburn.exe"
        try:
            subprocess.Popen([iso_burn_exe, str(self.current_meta.path)])
            self.notice_label.setText(f"Launched Windows Disc Image Burner for {self.current_meta.filename}")
        except Exception as e:
            self.notice_label.setText(f"Could not launch Windows Disc Burner: {e}")

    def _rebuild_operation_combo(self):
        meta = self.current_meta
        self.op_combo.blockSignals(True)
        self.op_combo.clear()
        self._filtered_items.clear()

        if not meta:
            self.op_combo.blockSignals(False)
            return

        if not meta.is_readable:
            self.op_combo.addItem("File is unreadable")
            self.convert_btn.setEnabled(False)
            self.batch_convert_btn.setEnabled(False)
            self.notice_label.setText("⚠️ File could not be opened or read.")
            self.op_combo.blockSignals(False)
            return

        query = self.op_filter_edit.text().strip().lower()
        for op in self.available_ops:
            label = f"{op.display_name} (.{op.output_format.upper()}) [{op.engine}]"
            if not query or query in label.lower() or query in op.id.lower() or query in op.output_format.lower():
                self._filtered_items.append(("cap", op))
                self.op_combo.addItem(label, op.id)

        for wf in self.available_workflows:
            step_names = " ➔ ".join(f".{s.output_format.upper()}" for s in wf.steps)
            label = f"🔗 Multi-Step Workflow: .{wf.source_format.upper()} ➔ {step_names} ({len(wf.steps)} steps)"
            if not query or query in label.lower() or query in wf.target_format.lower():
                self._filtered_items.append(("workflow", wf))
                self.op_combo.addItem(label, f"workflow:{wf.target_format}")

        self.op_combo.blockSignals(False)

        if not self._filtered_items:
            self.op_combo.addItem("No matching operations available")
            self.convert_btn.setEnabled(False)
            self.batch_convert_btn.setEnabled(False)
            self.notice_label.setText("ℹ️ Check Format Explorer for missing engines or clear search filter.")
            self._clear_settings_form()
        else:
            self.convert_btn.setEnabled(True)
            self.batch_convert_btn.setEnabled(len(self.files_meta) > 1)
            self._on_operation_changed(0)

    def _clear_settings_form(self):
        while self.settings_form.rowCount() > 0:
            self.settings_form.removeRow(0)
        self._setting_widgets.clear()

    def _on_operation_changed(self, idx: int):
        self._clear_settings_form()
        if idx < 0 or idx >= len(self._filtered_items):
            self.notice_label.setText("")
            return

        kind, item = self._filtered_items[idx]
        notices = []

        if kind == "cap":
            op: Capability = item
            if op.lossy:
                notices.append("ℹ️ Quality Note: Select 'Lossless / Exact Quality' above for maximum 100% fidelity (e.g., 4:4:4 chroma in JPEG or 320 kbps in Audio).")
            else:
                notices.append("✅ Lossless operation: Full source precision is preserved.")
            if op.limitations:
                notices.extend([f"• {lim}" for lim in op.limitations])
            self._build_settings_controls(op.settings_schema)
        else:
            wf: WorkflowPlan = item
            notices.append(f"🔗 Multi-Step Workflow Plan: {wf.summary()}")
            if wf.is_lossy:
                notices.append("⚠️ One or more steps in this workflow involve lossy encoding.")
            if wf.steps:
                first_cap = self.registry.get(wf.steps[0].capability_id)
                if first_cap:
                    self._build_settings_controls(first_cap.settings_schema)

        self.notice_label.setText("\n".join(notices))
        self._apply_preset_to_controls(self.quality_preset_combo.currentData())

    def _build_settings_controls(self, schema: Dict[str, Any]):
        if not schema:
            lbl = QLabel("Using optimal engine defaults for the selected Quality / Detail Level.")
            lbl.setStyleSheet("color: #8a8f98; font-style: italic;")
            self.settings_form.addRow(lbl)
            return

        for key, spec in schema.items():
            if key == "quality_preset":
                continue  # Handled by top-level Quality/Detail combo
            stype = spec.get("type", "str")
            label_txt = spec.get("label", key.replace("_", " ").title())
            default_val = spec.get("default")

            if stype == "int":
                spin = QSpinBox()
                spin.setRange(int(spec.get("min", 0)), int(spec.get("max", 10000)))
                spin.setValue(int(default_val if default_val is not None else 0))
                spin.setMinimumHeight(28)
                self._setting_widgets[key] = spin
                self.settings_form.addRow(f"{label_txt}:", spin)

            elif stype == "choice":
                combo = QComboBox()
                values = [str(v) for v in spec.get("values", [])]
                combo.addItems(values)
                if str(default_val) in values:
                    combo.setCurrentText(str(default_val))
                combo.setMinimumHeight(28)
                self._setting_widgets[key] = combo
                self.settings_form.addRow(f"{label_txt}:", combo)

            elif stype == "bool":
                chk = QCheckBox()
                chk.setChecked(bool(default_val))
                chk.setMinimumHeight(24)
                self._setting_widgets[key] = chk
                self.settings_form.addRow(f"{label_txt}:", chk)

            else:
                edit = QLineEdit(str(default_val or ""))
                edit.setMinimumHeight(28)
                self._setting_widgets[key] = edit
                self.settings_form.addRow(f"{label_txt}:", edit)

    def _on_quality_preset_changed(self, _idx: int):
        preset = self.quality_preset_combo.currentData()
        self._apply_preset_to_controls(preset)

    def _apply_preset_to_controls(self, preset: str):
        """Sync fine-grained controls when user picks a Quality/Detail preset."""
        if not preset or preset == "custom":
            return

        # Image quality & subsampling
        if "quality" in self._setting_widgets and isinstance(self._setting_widgets["quality"], QSpinBox):
            q_map = {"lossless": 100, "high": 95, "balanced": 85, "compact": 70}
            self._setting_widgets["quality"].setValue(q_map.get(preset, 95))

        if "subsampling" in self._setting_widgets and isinstance(self._setting_widgets["subsampling"], QComboBox):
            sub_combo: QComboBox = self._setting_widgets["subsampling"]
            if preset in ("lossless", "high"):
                sub_combo.setCurrentIndex(0)  # 4:4:4 (Lossless Chroma)
            else:
                sub_combo.setCurrentIndex(sub_combo.count() - 1)  # 4:2:0

        if "lossless" in self._setting_widgets and isinstance(self._setting_widgets["lossless"], QCheckBox):
            self._setting_widgets["lossless"].setChecked(preset == "lossless")

        if "lossless_alac" in self._setting_widgets and isinstance(self._setting_widgets["lossless_alac"], QCheckBox):
            self._setting_widgets["lossless_alac"].setChecked(preset == "lossless")

        # Audio bitrate & bit depth
        if "bitrate" in self._setting_widgets and isinstance(self._setting_widgets["bitrate"], QComboBox):
            b_map = {"lossless": "320k", "high": "256k", "balanced": "192k", "compact": "128k"}
            self._setting_widgets["bitrate"].setCurrentText(b_map.get(preset, "320k"))

        if "bit_depth" in self._setting_widgets and isinstance(self._setting_widgets["bit_depth"], QComboBox):
            d_map = {"lossless": "24", "high": "24", "balanced": "16", "compact": "16"}
            self._setting_widgets["bit_depth"].setCurrentText(d_map.get(preset, "24"))

        # Video CRF & preset
        if "crf" in self._setting_widgets and isinstance(self._setting_widgets["crf"], QSpinBox):
            crf_map = {"lossless": 14, "high": 18, "balanced": 23, "compact": 28}
            self._setting_widgets["crf"].setValue(crf_map.get(preset, 18))

        if "preset" in self._setting_widgets and isinstance(self._setting_widgets["preset"], QComboBox):
            p_map = {"lossless": "slow", "high": "medium", "balanced": "medium", "compact": "fast"}
            self._setting_widgets["preset"].setCurrentText(p_map.get(preset, "medium"))

        # Document / PDF DPI
        if "dpi" in self._setting_widgets and isinstance(self._setting_widgets["dpi"], QSpinBox):
            dpi_map = {"lossless": 300, "high": 250, "balanced": 150, "compact": 96}
            self._setting_widgets["dpi"].setValue(dpi_map.get(preset, 300))

    def collect_current_settings(self) -> Dict[str, Any]:
        """Gather active quality preset and all dynamic control values."""
        settings: Dict[str, Any] = {
            "quality_preset": self.quality_preset_combo.currentData() or "lossless"
        }
        for key, widget in self._setting_widgets.items():
            if isinstance(widget, QSpinBox):
                val = widget.value()
                if key in ("width", "height") and val == 0:
                    continue
                settings[key] = val
            elif isinstance(widget, QComboBox):
                txt = widget.currentText()
                if key in ("sample_rate", "channels", "scale_height") and txt == "0":
                    continue
                settings[key] = txt
            elif isinstance(widget, QCheckBox):
                settings[key] = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                settings[key] = widget.text().strip()
        return settings

    def _get_destination_dir(self) -> Optional[Path]:
        txt = self.output_dir_edit.text().strip()
        if txt:
            return Path(txt)
        return None

    def _start_conversion(self):
        idx = self.op_combo.currentIndex()
        if idx < 0 or idx >= len(self._filtered_items) or not self.current_meta:
            return

        kind, item = self._filtered_items[idx]
        settings = self.collect_current_settings()
        dest_dir = self._get_destination_dir()

        if kind == "cap":
            op: Capability = item
            self.job_requested.emit({
                "source_path": self.current_meta.path,
                "operation_id": op.id,
                "target_format": op.output_format,
                "engine": op.engine,
                "settings": settings,
                "destination_path": dest_dir,
            })
        else:
            wf: WorkflowPlan = item
            settings["workflow_plan"] = wf
            self.job_requested.emit({
                "source_path": self.current_meta.path,
                "operation_id": f"workflow.{wf.source_format}_to_{wf.target_format}",
                "target_format": wf.target_format,
                "engine": "workflow",
                "settings": settings,
                "destination_path": dest_dir,
            })

    def _start_batch_conversion(self):
        """Enqueue the currently selected operation for all compatible files in the workspace list."""
        idx = self.op_combo.currentIndex()
        if idx < 0 or idx >= len(self._filtered_items):
            return

        kind, item = self._filtered_items[idx]
        settings = self.collect_current_settings()
        dest_dir = self._get_destination_dir()

        for meta in self.files_meta:
            if not meta.is_readable or meta.is_empty:
                continue
            if kind == "cap":
                op: Capability = item
                if meta.detected_format.lower() in [f.lower() for f in op.input_formats] or "*" in op.input_formats:
                    self.job_requested.emit({
                        "source_path": meta.path,
                        "operation_id": op.id,
                        "target_format": op.output_format,
                        "engine": op.engine,
                        "settings": dict(settings),
                        "destination_path": dest_dir,
                    })
            else:
                wf: WorkflowPlan = item
                if meta.detected_format.lower() == wf.source_format.lower():
                    wf_settings = dict(settings)
                    wf_settings["workflow_plan"] = wf
                    self.job_requested.emit({
                        "source_path": meta.path,
                        "operation_id": f"workflow.{wf.source_format}_to_{wf.target_format}",
                        "target_format": wf.target_format,
                        "engine": "workflow",
                        "settings": wf_settings,
                        "destination_path": dest_dir,
                    })
