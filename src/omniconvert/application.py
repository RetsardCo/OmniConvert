"""Application entry point and lifecycle manager."""

import sys
from PySide6.QtWidgets import QApplication
from omniconvert.config.logger import setup_logging
from omniconvert.config.settings import AppSettings
from omniconvert.ui.main_window import MainWindow

def run_app():
    """Run OmniConvert desktop application."""
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("OmniConvert")
    app.setOrganizationName("OmniConvert")

    settings = AppSettings.load()
    window = MainWindow(settings)
    window.show()

    return app.exec()
