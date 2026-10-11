"""Application entry point and lifecycle manager."""

import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from omniconvert.config.logger import setup_logging
from omniconvert.config.settings import AppSettings
from omniconvert.config.paths import get_icon_path
from omniconvert.ui.main_window import MainWindow


def run_app():
    """Run OmniConvert desktop application."""
    setup_logging()

    # Set Windows AppUserModelID so the Windows taskbar displays our custom application icon
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OmniConvert.UniversalWorkspace.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("OmniConvert")
    app.setOrganizationName("OmniConvert")

    icon_path = get_icon_path(prefer_ico=True)
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    settings = AppSettings.load()
    window = MainWindow(settings)
    window.show()

    return app.exec()
