"""Home view / Landing page with drop area, custom branding icon, quick action cards, and recent conversions summary."""

from typing import List
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog
)

from omniconvert.config.paths import get_icon_path
from omniconvert.core.history import HistoryRecord


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("card")
        self.setMinimumHeight(170)
        self.setStyleSheet("""
            QFrame#card {
                border: 2px dashed #3b82f6;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_path = get_icon_path(prefer_ico=False)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("📁")
            icon_label.setStyleSheet("font-size: 40px;")
        icon_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel("Drag & Drop Files or Folders Here")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)

        sub_label = QLabel("Convert PDF ⇄ Word, Images (Lossless 100%), Audio/Video, Spreadsheets & Archives — 100% Offline")
        sub_label.setStyleSheet("color: #8a8f98; font-size: 13px;")
        sub_label.setAlignment(Qt.AlignCenter)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        browse_btn = QPushButton("Browse Files")
        browse_btn.setObjectName("primaryButton")
        browse_btn.setFixedWidth(150)
        browse_btn.clicked.connect(self._on_browse)

        folder_btn = QPushButton("Browse Folder")
        folder_btn.setFixedWidth(150)
        folder_btn.clicked.connect(self._on_browse_folder)

        btn_row.addStretch()
        btn_row.addWidget(browse_btn)
        btn_row.addWidget(folder_btn)
        btn_row.addStretch()

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(sub_label)
        layout.addSpacing(8)
        layout.addLayout(btn_row)

    def _on_browse(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Convert")
        if files:
            self.files_dropped.emit(files)

    def _on_browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Convert or Archive")
        if folder:
            self.files_dropped.emit([folder])

    def _set_drag_active(self, active: bool):
        if active:
            self.setStyleSheet("""
                QFrame#card {
                    border: 2px solid #22c55e;
                    border-radius: 12px;
                    background-color: rgba(34, 197, 94, 0.08);
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#card {
                    border: 2px dashed #3b82f6;
                    border-radius: 12px;
                }
            """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active(True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)
        event.accept()

    def dropEvent(self, event):
        self._set_drag_active(False)
        urls = event.mimeData().urls()
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if file_paths:
            self.files_dropped.emit(file_paths)
        event.acceptProposedAction()


class HomeView(QWidget):
    open_conversion = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header_row = QHBoxLayout()
        logo_lbl = QLabel()
        icon_path = get_icon_path(prefer_ico=False)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            header_row.addWidget(logo_lbl)
            header_row.addSpacing(10)

        title_col = QVBoxLayout()
        header = QLabel("Welcome to OmniConvert")
        header.setStyleSheet("font-size: 22px; font-weight: bold;")
        sub_header = QLabel("Universal local-first file conversion, document workflow, and media workspace.")
        sub_header.setStyleSheet("color: #8a8f98; font-size: 14px;")
        title_col.addWidget(header)
        title_col.addWidget(sub_header)
        header_row.addLayout(title_col)
        header_row.addStretch()

        layout.addLayout(header_row)

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._handle_files)
        layout.addWidget(self.drop_area)

        # Quick categories overview
        cat_label = QLabel("Supported Categories & Highlights")
        cat_label.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 4px;")
        layout.addWidget(cat_label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        categories = [
            ("📄 PDF ⇄ Word & Office", "PDF to Word (.docx) & Excel (.xlsx), Word/Excel/PPT to PDF, Markdown, HTML, TXT, CSV, JSON"),
            ("🖼️ Lossless Images", "PNG, JPEG (100% 4:4:4 Lossless Color), WebP, TIFF, BMP, GIF, SVG, Multi-Size .ICO"),
            ("🎵 Full Audio & Video", "MP3 (320k), WAV (24-bit PCM), FLAC, AAC, M4A (ALAC), OGG, OPUS, AIFF, MP4, MKV, WebM, GIF"),
            ("📦 Archives & Workflows", "ZIP, TAR, GZ, 7Z safe extraction/packing, Local TTS Speech, Binary Inspection"),
        ]

        for title, desc in categories:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            t = QLabel(title)
            t.setStyleSheet("font-weight: bold; font-size: 14px;")
            d = QLabel(desc)
            d.setStyleSheet("color: #8a8f98; font-size: 12px;")
            d.setWordWrap(True)
            card_layout.addWidget(t)
            card_layout.addWidget(d)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)

        # Recent Conversions Card
        recent_card = QFrame()
        recent_card.setObjectName("card")
        recent_layout = QVBoxLayout(recent_card)
        recent_title = QLabel("Recent Conversions")
        recent_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        recent_layout.addWidget(recent_title)

        self.recent_summary_label = QLabel("No recent conversions recorded yet.")
        self.recent_summary_label.setStyleSheet("color: #8a8f98; font-size: 12px;")
        self.recent_summary_label.setWordWrap(True)
        recent_layout.addWidget(self.recent_summary_label)

        layout.addWidget(recent_card)
        layout.addStretch()

    def refresh_recent(self, records: List[HistoryRecord]):
        if not records:
            self.recent_summary_label.setText("No recent conversions recorded yet.")
            return
        lines = []
        for rec in records[:4]:
            badge = "✅" if rec.status == "completed" else "❌"
            lines.append(
                f"{badge} {rec.source_name} ➔ .{rec.target_format.upper()} "
                f"({rec.operation_id}, {rec.duration_seconds:.2f}s)"
            )
        self.recent_summary_label.setText("\n".join(lines))

    def _handle_files(self, files: list):
        self.open_conversion.emit(files)
