"""Home view / Landing page with drop area, custom branding icon, and quick action cards."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QFileDialog
)

from omniconvert.config.paths import get_icon_path


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("card")
        self.setMinimumHeight(180)
        self.setStyleSheet("""
            QFrame#card {
                border: 2px dashed #3c424f;
                border-radius: 12px;
                background-color: rgba(255, 255, 255, 0.02);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_path = get_icon_path(prefer_ico=False)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("📁")
            icon_label.setStyleSheet("font-size: 42px; background: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel("Drag & Drop Files Here")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        title_label.setAlignment(Qt.AlignCenter)

        sub_label = QLabel("Convert PDF ⇄ Word, Images (Lossless 100%), Audio/Video, Spreadsheets & Archives — 100% Offline")
        sub_label.setStyleSheet("color: #8a8f98; font-size: 13px; background: transparent;")
        sub_label.setAlignment(Qt.AlignCenter)

        browse_btn = QPushButton("Browse Files")
        browse_btn.setObjectName("primaryButton")
        browse_btn.setFixedWidth(160)
        browse_btn.clicked.connect(self._on_browse)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(sub_label)
        layout.addSpacing(10)
        layout.addWidget(browse_btn, alignment=Qt.AlignCenter)

    def _on_browse(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Convert")
        if files:
            self.files_dropped.emit(files)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if file_paths:
            self.files_dropped.emit(file_paths)


class HomeView(QWidget):
    open_conversion = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

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
        layout.addSpacing(6)

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._handle_files)
        layout.addWidget(self.drop_area)

        # Quick categories overview
        cat_label = QLabel("Supported Categories & Highlights")
        cat_label.setStyleSheet("font-size: 15px; font-weight: 600; margin-top: 10px;")
        layout.addWidget(cat_label)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        categories = [
            ("📄 PDF ⇄ Word & Office", "PDF to Word (.docx), Word/Excel/PPT to PDF, Markdown, HTML, TXT, CSV, JSON"),
            ("🖼️ Lossless Images", "PNG, JPEG (100% 4:4:4 Lossless Color), WebP, TIFF, BMP, SVG, Multi-Size .ICO"),
            ("🎵 Full Audio & Video", "MP3 (320k), WAV (24-bit PCM), FLAC, AAC, M4A, OGG, OPUS, AIFF, MP4, MKV, WebM, GIF"),
            ("📦 Archives & Workflows", "ZIP, TAR.GZ, 7Z safe extraction/packing, Local TTS Speech, Binary Inspection"),
        ]

        for title, desc in categories:
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            t = QLabel(title)
            t.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
            d = QLabel(desc)
            d.setStyleSheet("color: #8a8f98; font-size: 12px; background: transparent;")
            d.setWordWrap(True)
            card_layout.addWidget(t)
            card_layout.addWidget(d)
            cards_layout.addWidget(card)

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _handle_files(self, files: list):
        self.open_conversion.emit(files)
