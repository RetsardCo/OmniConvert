# OmniConvert

**OmniConvert** is a Windows desktop application designed to convert, transform, extract, package, and inspect a broad range of file types from one unified interface.

## Key Features
- **Local-first & Offline-capable**: All processing happens entirely on your machine. No cloud uploads, no external APIs.
- **Content Inspection**: File type identification via headers & magic bytes, not just extensions.
- **Modular Engines**: Decoupled engines for media (FFmpeg), images (Pillow), documents (pypdf), archives, and data structures.
- **Safe Execution**: Conversions execute on background worker threads, preventing source overwrites and handling temporary workspaces cleanly.
- **PySide6 Native UI**: Responsive, modern Windows desktop experience with dark and light themes.

## Getting Started

### 1. Requirements
- Windows 10 / 11 (x64)
- Python 3.10+ (Recommended Python 3.11 - 3.13)
- Optional: FFmpeg (for media operations)

### 2. Installation
```powershell
# Clone or navigate to the repository
cd OmniConvert

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Application
```powershell
python app.py
```

### 4. Running Tests
```powershell
pytest
```
