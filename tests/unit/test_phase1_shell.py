"""Unit tests for Phase 1 imports and application setup."""

import pytest
import os
from pathlib import Path

def test_core_package_imports():
    """Verify core packages and application modules can be imported cleanly."""
    import omniconvert
    from omniconvert.config.paths import get_app_root, get_app_data_dir, get_temp_dir, get_logs_dir
    from omniconvert.config.settings import AppSettings
    from omniconvert.ui.theme import get_theme_stylesheet
    
    assert omniconvert.__version__ == "0.1.0"
    assert get_app_root().exists()
    assert get_app_data_dir().exists()
    assert get_temp_dir().exists()
    assert get_logs_dir().exists()

def test_settings_serialization(tmp_path, monkeypatch):
    """Verify settings save and load properly."""
    from omniconvert.config.settings import AppSettings
    import omniconvert.config.settings as settings_mod

    # Redirect app data dir to temporary folder
    monkeypatch.setattr(settings_mod, "get_app_data_dir", lambda: tmp_path)

    settings = AppSettings(theme="light", collision_policy="overwrite", max_concurrent_jobs=4)
    settings.save()

    loaded = AppSettings.load()
    assert loaded.theme == "light"
    assert loaded.collision_policy == "overwrite"
    assert loaded.max_concurrent_jobs == 4

def test_theme_stylesheets():
    """Verify dark and light stylesheets are returned."""
    from omniconvert.ui.theme import get_theme_stylesheet

    dark_qss = get_theme_stylesheet("dark")
    light_qss = get_theme_stylesheet("light")

    assert "#18191c" in dark_qss
    assert "#ffffff" in light_qss

def test_ui_responsive_during_simulated_task():
    """Confirm the UI remains responsive during a simulated background task using QThread."""
    import time
    from PySide6.QtCore import QThread, Signal, QObject
    from PySide6.QtWidgets import QApplication
    from omniconvert.ui.main_window import MainWindow

    class Worker(QObject):
        finished = Signal(str)

        def run(self):
            # Simulate work
            time.sleep(0.05)
            self.finished.emit("done")

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    thread = QThread()
    worker = Worker()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    result = []
    worker.finished.connect(lambda val: result.append(val))
    worker.finished.connect(thread.quit)

    thread.start()
    # Process events while thread runs to ensure UI event loop is non-blocking
    for _ in range(100):
        app.processEvents()
        if result:
            break
        time.sleep(0.01)

    thread.quit()
    thread.wait(2000)
    app.processEvents()
    assert result == ["done"]

def test_pyside_mainwindow_headless():
    """Test PySide6 MainWindow instantiation in offscreen/headless mode."""
    # Run in offscreen mode to support headless test environments
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from omniconvert.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    assert window.windowTitle().startswith("OmniConvert")
    assert window.stack.count() == 6
    assert window.active_jobs_count == 0

    # Test tab navigation
    window._on_nav_clicked(1)
    assert window.stack.currentIndex() == 1

    # Test file reception trigger
    test_files = ["C:\\dummy\\image.png", "C:\\dummy\\sample.pdf"]
    window._on_files_received(test_files)
    assert window.stack.currentIndex() == 1
    assert window.conversion_view.file_list.count() == 2
