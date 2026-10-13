# Changelog

All notable changes to **OmniConvert** are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0-alpha] - 2026-10-12

> **First public pre-release.** All core features are functional. Expect rough
> edges — please [file issues](https://github.com/RetsardCo/OmniConvert/issues)
> if you encounter bugs.

### 🎉 Highlights
- 70+ file format conversions across documents, images, audio, video, archives, and data — **100% offline, zero cloud**.
- Direct PDF to Excel (`.xlsx`) table extraction with numeric parsing and sheet-per-page options.
- 5 distribution packages: Lite, +OCR, +Whisper, Full, and Windows Installer.
- Qt 6 desktop GUI with drag-and-drop, batch & merge tools, quality presets, and conversion history.

### Added — Core Engines
- **Document & Office Suite**: PDF ↔ Word (`.docx`), PDF ➔ Excel (`.xlsx`), PowerPoint (`.pptx`), HTML, Markdown, CSV, JSON, TXT — fully offline via pure-Python engines (`reportlab`, `python-docx`, `openpyxl`, `python-pptx`, `pdf2docx`, `PyMuPDF`) or optional LibreOffice headless.
- **PDF Toolkit**: PDF → Excel spreadsheet (`.xlsx`) table extraction, PDF → high-DPI images (PNG/JPEG), PDF → HTML, PDF → Markdown, PDF merge, images → PDF.
- **Image Processing**: PNG, JPEG, BMP, TIFF, WebP, GIF, ICO, SVG, and Apple HEIC/HEIF (`pillow-heif`). Quality presets from lossless (4:4:4 chroma, quality 100) through compact.
- **Audio Transcoding**: MP3, WAV (16/24/32-bit PCM), FLAC, AAC, M4A (AAC + ALAC), OGG Vorbis, Opus, AIFF — with bitrate, sample rate, and channel controls via FFmpeg.
- **Video Transcoding**: MP4, MKV, WebM, MOV, AVI, animated GIF. Audio extraction, subtitle extraction, FFprobe metadata → JSON, CSV → animated bar-chart video.
- **Archives & Compression**: ZIP, TAR, TAR.GZ/TGZ, GZ, 7Z — list, extract, create, and cross-format repack with Zip-Slip protection, symlink blocking, and decompression-bomb limits.
- **ISO / Optical Disc**: ISO 9660 & Joliet inspection, extraction, and directory creation (`pycdlib`); Windows `isoburn.exe` integration.
- **Cross-Category Workflow Planner**: Bounded shortest-path BFS across all registered single-step capabilities (e.g., `docx → txt → wav`).

### Fixed
- **Multi-Instance Window Spawning**: Eliminated extra application instances opening during background conversions by adding `multiprocessing.freeze_support()`, CLI worker mode argument dispatch in `app.py`, and `QLocalServer`/`QLocalSocket` single-instance IPC enforcement.
- **Clean Application Termination**: Added `JobManager.shutdown()` in `MainWindow.closeEvent` to cancel active thread pool jobs and terminate orphan processes when closing the window.
- **Text-to-Speech Audio ("sssssstt" hissing)**: Fixed corrupted audio synthesis by adding proper Windows COM apartment initialization (`CoInitialize`/`CoUninitialize`), headless CLI subprocess fallback, and harmonic waveform synthesis.

### Added — Optional AI Engines (bundled in OCR / Whisper / Full packages)
- **Tesseract OCR** (`OCREngine`): Image-to-text via portable Tesseract 5.4 binaries with auto `TESSDATA_PREFIX` configuration.
- **Whisper ASR** (`ASREngine`): Audio-to-text via faster-whisper (CTranslate2 `tiny.en` model). Includes PyAV 19.x compatibility patch.
- **TTS** (`TTSEngine`): Offline text-to-speech via Windows SAPI5 / `pyttsx3` with deterministic PCM WAV fallback.
- **Binary Inspector** (`BinaryEngine`): Strings extraction, SHA-256 hashes, Shannon entropy, PE header parsing, and hex dumps.

### Added — UI & UX
- Qt 6 (`PySide6`) main window with sidebar navigation: Home, Conversion Workspace, Batch & Merge, Queue, History, Format Explorer, Settings.
- Drag-and-drop file input with multi-file selection.
- Global quality / detail level selector (Lossless, High, Balanced, Compact, Custom) with per-operation parameter schemas.
- Full hover-detail tooltips displaying untruncated text across all views.
- Responsive layout scaling for windowed and maximized modes.
- Confirmation dialogs on clearing files or cancelling jobs.
- `Remove Selected` button and keyboard shortcuts (`Delete` / `Backspace`).
- Persistent conversion history with search and "Open Folder" / "Retry" actions.
- Searchable Format Explorer showing all supported conversions.
- Settings view with live local-dependency and privacy reporting.

### Added — Batch & Merge
- **PDF Merge**: Combine multiple PDFs into one (`pypdf.PdfWriter`).
- **Images → PDF**: Multi-page document generation from image collections.
- **Images → Animated GIF**: Multi-frame GIF with configurable frame duration.
- Dedicated "📦 Batch & Merge Tools" workspace grid.

### Added — Distribution & Packaging
- `scripts/prepare_engines.py` — stages Tesseract binaries and Whisper model weights.
- `scripts/build_releases.py` — master automation: PyInstaller → 4 portable ZIPs → Inno Setup installer.
- `scripts/installer.iss` — Inno Setup 6 script with optional OCR and Whisper components.
- Multi-resolution Windows `.ico` (16×16 → 256×256) and PNG application icon.
- PyInstaller `--onedir` packaging with `--windowed --icon` flags.

### Added — Quality & Testing
- 78 unit tests across 12 test modules — all passing.
- `scripts/check_dependencies.py` for build-time dependency verification.
