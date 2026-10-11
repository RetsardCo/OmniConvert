"""UI Conversion Workspace View connecting file detector, capability registry, and options."""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QComboBox, QTextEdit, QFileDialog,
    QSplitter, QMessageBox
)

from omniconvert.core.file_detector import inspect_file, FileMetadata
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.models.capability import Capability

class ConversionWorkspaceView(QWidget):
    job_requested = Signal(dict)

    def __init__(self, registry: CapabilityRegistry = None, parent=None):
        super().__init__(parent)
        self.registry = registry or CapabilityRegistry()
        self.files_meta: list[FileMetadata] = []
        self.current_meta: FileMetadata | None = None
        self.available_ops: list[Capability] = []

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Conversion Workspace")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        sub_title = QLabel("Inspect files, select operations, and configure outputs.")
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

        # Splitter: Left (Files List) | Right (Inspection & Operation Selection)
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

        # Right: Details & Operations Card
        right_card = QFrame()
        right_card.setObjectName("card")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

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
        self.meta_text.setFixedHeight(120)
        right_layout.addWidget(self.meta_text)

        # Operation Selector
        op_lbl = QLabel("Choose Operation:")
        op_lbl.setStyleSheet("font-weight: 600; background: transparent;")
        right_layout.addWidget(op_lbl)

        self.op_combo = QComboBox()
        self.op_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2f38;
                border: 1px solid #3c424f;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f0f2f5;
            }
        """)
        self.op_combo.currentIndexChanged.connect(self._on_operation_changed)
        right_layout.addWidget(self.op_combo)

        # Warning / Limitation Notice
        self.notice_label = QLabel("")
        self.notice_label.setWordWrap(True)
        self.notice_label.setStyleSheet("color: #eab308; font-size: 12px; background: transparent;")
        right_layout.addWidget(self.notice_label)

        right_layout.addStretch()

        # Action: Convert Button
        bottom_box = QHBoxLayout()
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

    def add_files(self, paths: list):
        for p in paths:
            meta = inspect_file(p)
            # Avoid duplicate paths
            if any(m.path == meta.path for m in self.files_meta):
                continue
            self.files_meta.append(meta)

            status_icon = "⚠️" if meta.error or not meta.is_readable else "📄"
            item = QListWidgetItem(f"{status_icon} {meta.filename} ({meta.formatted_size})")
            self.file_list.addItem(item)

        if self.file_list.count() > 0 and self.file_list.currentRow() == -1:
            self.file_list.setCurrentRow(0)

    def clear_files(self):
        self.files_meta.clear()
        self.file_list.clear()
        self.current_meta = None
        self.available_ops.clear()
        self.details_label.setText("Select a file from the list to inspect details.")
        self.meta_text.clear()
        self.op_combo.clear()
        self.notice_label.setText("")
        self.convert_btn.setEnabled(False)

    def _on_file_selected(self, row: int):
        if row < 0 or row >= len(self.files_meta):
            return
        meta = self.files_meta[row]
        self.current_meta = meta

        self.details_label.setText(f"Inspecting: {meta.filename}")
        info_lines = [
            f"Path: {meta.path}",
            f"Size: {meta.formatted_size} ({meta.size_bytes:,} bytes)",
            f"Detected Format: {meta.detected_format.upper()}",
            f"Category: {meta.category.capitalize()}",
            f"MIME: {meta.detected_mime}",
            f"Readable: {'Yes' if meta.is_readable else 'No'}",
        ]
        if meta.error:
            info_lines.append(f"Error: {meta.error}")
        self.meta_text.setText("\n".join(info_lines))

        # Query Registry
        self.available_ops = self.registry.find_operations_for_file(meta, only_available=True)
        self.op_combo.clear()

        if not meta.is_readable:
            self.op_combo.addItem("File is unreadable")
            self.convert_btn.setEnabled(False)
            self.notice_label.setText("⚠️ File could not be opened or read.")
        elif not self.available_ops:
            self.op_combo.addItem("No available operations for this file type")
            self.convert_btn.setEnabled(False)
            self.notice_label.setText("ℹ️ Check Format Explorer for missing engines or unsupported formats.")
        else:
            for op in self.available_ops:
                self.op_combo.addItem(f"{op.display_name} [{op.engine}]", op.id)
            self.convert_btn.setEnabled(True)

    def _on_operation_changed(self, idx: int):
        if idx < 0 or idx >= len(self.available_ops):
            self.notice_label.setText("")
            return
        op = self.available_ops[idx]
        notices = []
        if op.lossy:
            notices.append("⚠️ Lossy operation: Some data, precision, or transparency may be modified.")
        if op.limitations:
            notices.extend([f"• {lim}" for lim in op.limitations])
        self.notice_label.setText("\n".join(notices))

    def _start_conversion(self):
        idx = self.op_combo.currentIndex()
        if idx < 0 or idx >= len(self.available_ops) or not self.current_meta:
            return
        op = self.available_ops[idx]
        self.job_requested.emit({
            "source_path": self.current_meta.path,
            "operation_id": op.id,
            "target_format": op.output_format,
            "engine": op.engine
        })
