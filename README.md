# OmniConvert

**OmniConvert** is a universal Windows desktop file-processing and conversion workspace designed to convert, transform, extract, package, and inspect a broad range of file types from one unified, 100% local interface.

## Key Features
- **Local-First & Offline-Capable**: All processing happens entirely on your machine. No cloud uploads, no external APIs, and no telemetry.
- **Full Document & Office Suite**:
  - **PDF to Word (`.pdf` -> `.docx`)** with layout, table, paragraph, and image preservation (`pdf2docx`, `PyMuPDF`, `python-docx`).
  - **Word to PDF (`.docx` -> `.pdf`)**, Excel (`.xlsx` <-> `.pdf`, `.csv`, `.json`, `.html`), PowerPoint (`.pptx` -> `.pdf`, `.txt`), and Text/Markdown/HTML -> `.pdf`/`.docx` (`reportlab`, `openpyxl`, `python-pptx`, `markdown`, plus automatic LibreOffice escalation if installed).
  - **PDF to High-DPI Images (`.png`, `.jpeg`)**, **PDF to HTML**, **PDF to Markdown**, **PDF Text Extraction**, and **PDF Metadata to JSON**.
- **Quality & Detail Level Controls**:
  - Dedicated **Quality / Detail Level** presets (`Lossless / Exact Quality (100%)`, `High Quality`, `Balanced`, `Compact`, `Custom`) plus granular schema parameters.
  - True **100% quality 4:4:4 chroma (`subsampling=0`)** for PNG-to-JPEG conversion and lossless WebP/PNG/TIFF.
- **Complete Audio & Video Suite (FFmpeg)**:
  - Audio conversions across `mp3` (up to `320k` `-q:a 0`), `wav` (`16`/`24`/`32`-bit PCM), `flac` (lossless), `aac`, `m4a` (AAC and Apple Lossless `ALAC`), `ogg` (Vorbis), `opus`, and `aiff` with bitrate, sample rate, and channel controls.
  - Video transcoding (`mp4`, `mkv`, `webm`, `mov`, `avi`, `gif`), audio extraction, subtitle extraction, FFprobe metadata inspection, and CSV-to-MP4 animated bar-chart visualization.
- **Hardened Archive & Compression Engine**:
  - Create, inspect, extract, and repack `zip`, `tar`, `tar.gz`/`tgz`, `gz`, and `7z` (`py7zr`) archives with built-in Zip-Slip path traversal prevention, symlink blocking, and decompression bomb safeguards.
- **Cross-Category Multi-Step Workflow Planner**:
  - Automatically discovers bounded multi-step conversion pipelines across engines (e.g., `DOCX -> TXT -> WAV` audiobook synthesis, `Archive -> Combined PDF`, `Image -> OCR -> Audio`) with intermediate artifact validation.
- **Offline Speech, Optional OCR & Static Binary Inspection**:
  - Local Text-to-Speech (`SAPI5`/`pyttsx3`), optional local Tesseract OCR, optional Whisper ASR, and static executable/binary inspection (`MD5`/`SHA-1`/`SHA-256`, Shannon entropy, PE headers, printable strings, hex dump).

## Getting Started

### 1. Requirements
- Windows 10 / 11 (x64)
- Python 3.10+ (Tested on Python 3.13)
- Local FFmpeg (`winget install Gyan.FFmpeg` — automatically detected in PATH or WinGet packages)

### 2. Installation
```powershell
# Navigate to the repository
cd OmniConvert

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt
```

### 3. Running the Application
```powershell
.\.venv\Scripts\python.exe app.py
```

### 4. Checking Local Dependencies & Building Windows Package
```powershell
# Print JSON dependency & capability report
.\.venv\Scripts\python.exe scripts\check_dependencies.py

# Build standalone Windows package via PyInstaller (use --dry-run to preview command)
.\.venv\Scripts\python.exe scripts\build_windows.py
```

### 5. Running the Automated Test Suite
```powershell
.\.venv\Scripts\pytest.exe -v
```

See [SUPPORTED_FORMATS.md](SUPPORTED_FORMATS.md) for the complete verified capability matrix and [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for third-party license notices.
