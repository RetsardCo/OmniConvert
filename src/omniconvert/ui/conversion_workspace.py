"""UI Conversion Workspace View connecting file detector, capability registry, workflow planner, and quality/detail controls."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QComboBox, QTextEdit, QFileDialog,
    QSplitter, QMessageBox, QFormLayout, QSpinBox, QCheckBox, QLineEdit,
    QScrollArea
)

from omniconvert.core.file_detector import inspect_file, FileMetadata
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.core.planner import WorkflowPlanner
from omniconvert.models.capability import Capability
from omniconvert.models.workflow import WorkflowPlan


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
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_files)

        top_bar.addWidget(add_btn)
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

        left_title = QLabel("Input Files")
        left_title.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        left_layout.addWidget(left_title)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #2d3036;
                border-radius: 6px;
                background-color: #1a1b1f;
                color: #f0f2f5;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background-color: #0066cc;
                color: #ffffff;
            }
        """)
        self.file_list.currentRowChanged.connect(self._on_file_selected)
        left_layout.addWidget(self.file_list)
        splitter.addWidget(left_card)

        # Right: Details, Operation, Quality Preset & Settings Card
        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 14, 16, 14)
        right_layout.setSpacing(10)

        self.details_label = QLabel("Select a file from the list to inspect details.")
        self.details_label.setStyleSheet("font-size: 14px; font-weight: 600; background: transparent;")
        right_layout.addWidget(self.details_label)

        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        self.meta_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #2d3036;
                border-radius: 6px;
                background-color: #1a1b1f;
                color: #cfd5dc;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        self.meta_text.setFixedHeight(88)
        right_layout.addWidget(self.meta_text)

        # Operation Search & Selector Row
        op_header_row = QHBoxLayout()
        op_lbl = QLabel("Choose Operation / Target Format:")
        op_lbl.setStyleSheet("font-weight: 600; background: transparent;")
        op_header_row.addWidget(op_lbl)
        op_header_row.addStretch()

        self.op_filter_edit = QLineEdit()
        self.op_filter_edit.setPlaceholderText("🔍 Filter operations (e.g. docx, pdf, mp3, wav)...")
        self.op_filter_edit.setFixedWidth(250)
        self.op_filter_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1b1f;
                border: 1px solid #3c424f;
                border-radius: 5px;
                padding: 4px 8px;
                color: #f0f2f5;
                font-size: 12px;
            }
        """)
        self.op_filter_edit.textChanged.connect(self._rebuild_operation_combo)
        op_header_row.addWidget(self.op_filter_edit)
        right_layout.addLayout(op_header_row)

        self.op_combo = QComboBox()
        self.op_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2f38;
                border: 1px solid #3c424f;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f0f2f5;
                font-weight: 500;
            }
        """)
        self.op_combo.currentIndexChanged.connect(self._on_operation_changed)
        right_layout.addWidget(self.op_combo)

        # Global Quality / Detail Level Selector
        quality_row = QHBoxLayout()
        q_lbl = QLabel("🎯 Conversion Quality & Detail Level:")
        q_lbl.setStyleSheet("font-weight: 600; color: #60a5fa; background: transparent;")
        quality_row.addWidget(q_lbl)

        self.quality_preset_combo = QComboBox()
        self.quality_preset_combo.addItem("💎 Lossless / Exact Quality (100% Detail & Fidelity)", "lossless")
        self.quality_preset_combo.addItem("✨ High Quality (Detailed - 95% / 256 kbps / 300 DPI)", "high")
        self.quality_preset_combo.addItem("⚖️ Balanced (Standard - 85% / 192 kbps / 150 DPI)", "balanced")
        self.quality_preset_combo.addItem("⚡ Compact / Fast (Compressed - 70% / 128 kbps / 96 DPI)", "compact")
        self.quality_preset_combo.addItem("🎛️ Custom (Adjust Fine-Grained Controls Below)", "custom")
        self.quality_preset_combo.setStyleSheet("""
            QComboBox {
                background-color: #1e293b;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 5px 10px;
                color: #f8fafc;
                font-weight: 600;
            }
        """)
        self.quality_preset_combo.currentIndexChanged.connect(self._on_quality_preset_changed)
        quality_row.addWidget(self.quality_preset_combo, stretch=1)
        right_layout.addLayout(quality_row)

        # Dynamic Context-Sensitive Settings Area
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setMaximumHeight(150)
        self.settings_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #2d3036;
                border-radius: 6px;
                background-color: #1a1b1f;
            }
        """)
        self.settings_container = QWidget()
        self.settings_container.setStyleSheet("background-color: #1a1b1f;")
        self.settings_form = QFormLayout(self.settings_container)
        self.settings_form.setContentsMargins(12, 8, 12, 8)
        self.settings_form.setSpacing(6)
        self.settings_scroll.setWidget(self.settings_container)
        right_layout.addWidget(self.settings_scroll)

        # Output Folder Selector
        out_row = QHBoxLayout()
        out_lbl = QLabel("Output Folder:")
        out_lbl.setStyleSheet("font-weight: 500; background: transparent;")
        self.output_dir_edit = QLineEdit(self.default_output_dir)
        self.output_dir_edit.setPlaceholderText("Default: Same folder as source file")
        self.output_dir_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1b1f;
                border: 1px solid #3c424f;
                border-radius: 5px;
                padding: 5px 8px;
                color: #f0f2f5;
            }
        """)
        out_browse_btn = QPushButton("Browse...")
        out_browse_btn.clicked.connect(self._browse_output_dir)
        out_row.addWidget(out_lbl)
        out_row.addWidget(self.output_dir_edit, stretch=1)
        out_row.addWidget(out_browse_btn)
        right_layout.addLayout(out_row)

        # Warning / Limitation / Workflow Step Notice
        self.notice_label = QLabel("")
        self.notice_label.setWordWrap(True)
        self.notice_label.setStyleSheet("color: #eab308; font-size: 12px; background: transparent;")
        right_layout.addWidget(self.notice_label)

        right_layout.addStretch()

        # Action: Convert Selected & Convert All Batch Buttons
        bottom_box = QHBoxLayout()
        self.batch_convert_btn = QPushButton("Convert All Compatible Files")
        self.batch_convert_btn.setEnabled(False)
        self.batch_convert_btn.clicked.connect(self._start_batch_conversion)
        bottom_box.addWidget(self.batch_convert_btn)

        bottom_box.addStretch()

        self.convert_btn = QPushButton("Start Conversion")
        self.convert_btn.setObjectName("primaryButton")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_conversion)
        bottom_box.addWidget(self.convert_btn)
        right_layout.addLayout(bottom_box)

        splitter.addWidget(right_card)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        main_layout.addWidget(splitter)

    def _browse_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files to Add")
        if paths:
            self.add_files(paths)

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

            status_icon = "⚠️" if meta.error or not meta.is_readable else "📄"
            item = QListWidgetItem(f"{status_icon} {meta.filename} ({meta.formatted_size}) [{meta.detected_format.upper()}]")
            self.file_list.addItem(item)

        if self.file_list.count() > 0 and self.file_list.currentRow() == -1:
            self.file_list.setCurrentRow(0)

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
        if meta.error:
            info_lines.append(f"Error: {meta.error}")
        self.meta_text.setText("\n".join(info_lines))

        self.available_ops = self.registry.find_operations_for_file(meta, only_available=True)
        self.available_workflows = (
            self.planner.find_multi_step_targets_for_format(meta.detected_format, only_available=True)
            if meta.is_readable and not meta.is_empty
            else []
        )
        self._rebuild_operation_combo()

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
            # Use first step's schema if present
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
                spin.setStyleSheet("background-color: #2b2f38; color: #f0f2f5; padding: 3px; border: 1px solid #3c424f; border-radius: 4px;")
                self._setting_widgets[key] = spin
                self.settings_form.addRow(f"{label_txt}:", spin)

            elif stype == "choice":
                combo = QComboBox()
                values = [str(v) for v in spec.get("values", [])]
                combo.addItems(values)
                if str(default_val) in values:
                    combo.setCurrentText(str(default_val))
                combo.setStyleSheet("background-color: #2b2f38; color: #f0f2f5; padding: 3px; border: 1px solid #3c424f; border-radius: 4px;")
                self._setting_widgets[key] = combo
                self.settings_form.addRow(f"{label_txt}:", combo)

            elif stype == "bool":
                chk = QCheckBox()
                chk.setChecked(bool(default_val))
                self._setting_widgets[key] = chk
                self.settings_form.addRow(f"{label_txt}:", chk)

            else:
                edit = QLineEdit(str(default_val or ""))
                edit.setStyleSheet("background-color: #2b2f38; color: #f0f2f5; padding: 3px; border: 1px solid #3c424f; border-radius: 4px;")
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
