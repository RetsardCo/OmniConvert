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
    import logging
    settings = AppSettings.load()
    level_val = getattr(logging, str(settings.log_level).upper(), logging.INFO)
    setup_logging(level=level_val)

    # Set Windows AppUserModelID so the Windows taskbar displays our custom application icon
    if os.name == "nt":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OmniConvert.UniversalWorkspace.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("OmniConvert")
    app.setOrganizationName("OmniConvert")

    # Single-instance enforcement: ensure only one GUI instance of the application runs
    server_name = "OmniConvert_SingleInstance_IPC"
    allow_multiple = os.environ.get("OMNICONVERT_ALLOW_MULTIPLE_INSTANCES", "0") == "1"
    local_server = None

    if not allow_multiple:
        from PySide6.QtNetwork import QLocalSocket, QLocalServer
        socket = QLocalSocket()
        socket.connectToServer(server_name)
        if socket.waitForConnected(300):
            # Another instance is already running: signal it to activate and exit
            socket.write(b"ACTIVATE\n")
            socket.flush()
            socket.disconnectFromServer()
            logging.info("Existing OmniConvert instance detected. Activated window and exiting secondary process.")
            return 0

        # Primary instance: create local IPC server
        local_server = QLocalServer()
        QLocalServer.removeServer(server_name)
        local_server.listen(server_name)

    icon_path = get_icon_path(prefer_ico=True)
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow(settings)

    if local_server:
        def _on_new_instance():
            client = local_server.nextPendingConnection()
            if client:
                client.waitForReadyRead(300)
                client.disconnectFromServer()
                window.showNormal()
                window.raise_()
                window.activateWindow()
        local_server.newConnection.connect(_on_new_instance)

    window.show()

    ret = app.exec()
    if local_server and local_server.isListening():
        local_server.close()
        from PySide6.QtNetwork import QLocalServer
        QLocalServer.removeServer(server_name)
    return ret

