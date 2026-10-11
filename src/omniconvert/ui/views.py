"""Placeholder and workspace views for queue, history, settings, and format explorer."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QHBoxLayout

class ConversionView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Conversion Workspace")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Inspect files, select operations, and configure outputs.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px; margin-bottom: 15px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        self.file_label = QLabel("No files loaded. Drag and drop files from the Home view or browse.")
        self.file_label.setStyleSheet("color: #8a8f98; font-style: italic; background: transparent;")
        c_layout.addWidget(self.file_label)
        layout.addWidget(card)
        layout.addStretch()

    def set_files(self, files: list):
        if files:
            self.file_label.setText(f"Loaded {len(files)} file(s):\n" + "\n".join(files[:5]))
            if len(files) > 5:
                self.file_label.setText(self.file_label.text() + f"\n...and {len(files)-5} more.")


class QueueView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Job Queue & Execution")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Active background conversion jobs and thread status.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px; margin-bottom: 15px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        status_lbl = QLabel("No active jobs currently running.")
        status_lbl.setStyleSheet("color: #8a8f98; background: transparent;")
        c_layout.addWidget(status_lbl)
        layout.addWidget(card)
        layout.addStretch()


class HistoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Conversion History")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Recent conversion logs, completion timestamps, and quick destination links.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px; margin-bottom: 15px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        lbl = QLabel("No past conversion records yet.")
        lbl.setStyleSheet("color: #8a8f98; background: transparent;")
        c_layout.addWidget(lbl)
        layout.addWidget(card)
        layout.addStretch()


class FormatExplorerView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Format Explorer & Capability Matrix")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Explore supported file formats, engines, limitations, and requirements.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px; margin-bottom: 15px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        info = QLabel(
            "Capabilities are dynamically registered.\n\n"
            "• Images: PNG, JPEG, WEBP, BMP, ICO (Pillow Engine)\n"
            "• Documents: PDF text extraction and merging (pypdf Engine)\n"
            "• Media: Audio and video transcoding (FFmpeg Engine)\n"
            "• Archives: ZIP, TAR extraction and compression (Archive Engine)"
        )
        info.setStyleSheet("background: transparent; line-height: 1.5;")
        c_layout.addWidget(info)
        layout.addWidget(card)
        layout.addStretch()


class SettingsView(QWidget):
    def __init__(self, parent=None, on_theme_toggle=None):
        super().__init__(parent)
        self.on_theme_toggle = on_theme_toggle
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Settings & Preferences")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        desc = QLabel("Manage output paths, collision policies, concurrent jobs, and UI themes.")
        desc.setStyleSheet("color: #8a8f98; font-size: 13px; margin-bottom: 15px;")
        layout.addWidget(title)
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Interface Theme:")
        theme_lbl.setStyleSheet("font-weight: 500; background: transparent;")
        self.toggle_theme_btn = QPushButton("Toggle Dark / Light Theme")
        if self.on_theme_toggle:
            self.toggle_theme_btn.clicked.connect(self.on_theme_toggle)
        theme_row.addWidget(theme_lbl)
        theme_row.addStretch()
        theme_row.addWidget(self.toggle_theme_btn)

        c_layout.addLayout(theme_row)
        layout.addWidget(card)
        layout.addStretch()
