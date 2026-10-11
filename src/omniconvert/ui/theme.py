"""Theme definitions and stylesheet generation for PySide6."""

from typing import Literal

DARK_THEME_QSS = """
QMainWindow {
    background-color: #18191c;
    color: #e3e5e8;
}

QWidget {
    background-color: #18191c;
    color: #e3e5e8;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

/* Sidebar navigation */
#sidebar {
    background-color: #1f2125;
    border-right: 1px solid #2d3036;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #9ba1a6;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

#sidebar QPushButton:hover {
    background-color: #2b2e35;
    color: #ffffff;
}

#sidebar QPushButton:checked {
    background-color: #0066cc;
    color: #ffffff;
    font-weight: bold;
}

/* Status bar */
QStatusBar {
    background-color: #1f2125;
    color: #8a8f98;
    border-top: 1px solid #2d3036;
    font-size: 12px;
}

/* Content cards */
.QFrame#card {
    background-color: #22252a;
    border: 1px solid #2d3139;
    border-radius: 8px;
    padding: 16px;
}

/* Buttons */
QPushButton {
    background-color: #2b2f38;
    color: #f0f2f5;
    border: 1px solid #3c424f;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383e4a;
    border-color: #4f5767;
}

QPushButton:pressed {
    background-color: #20242b;
}

QPushButton#primaryButton {
    background-color: #0066cc;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #0077ee;
}

QPushButton#primaryButton:pressed {
    background-color: #0055aa;
}

/* Progress bar */
QProgressBar {
    border: 1px solid #333740;
    border-radius: 4px;
    background-color: #1a1b1f;
    text-align: center;
    color: #ffffff;
}

QProgressBar::chunk {
    background-color: #0077ee;
    border-radius: 3px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #18191c;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #373b44;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #4f5461;
}
"""

LIGHT_THEME_QSS = """
QMainWindow {
    background-color: #f7f9fa;
    color: #1f2328;
}

QWidget {
    background-color: #f7f9fa;
    color: #1f2328;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
}

/* Sidebar navigation */
#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e1e4e8;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #57606a;
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}

#sidebar QPushButton:hover {
    background-color: #f3f4f6;
    color: #1f2328;
}

#sidebar QPushButton:checked {
    background-color: #0969da;
    color: #ffffff;
    font-weight: bold;
}

/* Status bar */
QStatusBar {
    background-color: #ffffff;
    color: #57606a;
    border-top: 1px solid #e1e4e8;
    font-size: 12px;
}

/* Content cards */
.QFrame#card {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    padding: 16px;
}

/* Buttons */
QPushButton {
    background-color: #f6f8fa;
    color: #24292f;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #eaeef2;
    border-color: #b5bcc4;
}

QPushButton:pressed {
    background-color: #dfdfe2;
}

QPushButton#primaryButton {
    background-color: #0969da;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #1177ee;
}

QPushButton#primaryButton:pressed {
    background-color: #0656b6;
}

/* Progress bar */
QProgressBar {
    border: 1px solid #d0d7de;
    border-radius: 4px;
    background-color: #eaeef2;
    text-align: center;
    color: #24292f;
}

QProgressBar::chunk {
    background-color: #0969da;
    border-radius: 3px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #f7f9fa;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cfd5dc;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #aab2bd;
}
"""

def get_theme_stylesheet(theme: Literal["dark", "light"] = "dark") -> str:
    """Return CSS/QSS for the requested theme."""
    return DARK_THEME_QSS if theme == "dark" else LIGHT_THEME_QSS
