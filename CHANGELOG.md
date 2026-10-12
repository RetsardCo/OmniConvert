# Changelog

All notable changes to **OmniConvert** are documented in this file.

## [0.1.0] - 2026-10-12 (Pre-Release Development Build)

### Added
- **Multi-Tier Distribution & Release Pipeline (5 Release Packages in `dist/releases/`)**:
  - `OmniConvert-Portable-Lite.zip`: Core standalone application (~110 MB) supporting 70+ formats with zero AI weights.
  - `OmniConvert-Portable-OCR.zip`: Core application with pre-bundled portable Tesseract OCR engine in `bin/tesseract/`.
  - `OmniConvert-Portable-Whisper.zip`: Core application with pre-bundled faster-whisper CTranslate2 model in `resources/models/whisper/`.
  - `OmniConvert-Portable-Full.zip`: Zero-download "Swiss Army Knife" featuring both pre-bundled OCR and Whisper speech-to-text models.
  - `OmniConvert-Setup.exe`: Inno Setup 6 smart installer with component checkboxes for custom installation.
- **UI / UX Polish & Accessibility**:
  - Full hover detail tooltips displaying untruncated text across the Format Explorer, Conversion Workspace, and History views.
  - Responsive layout scaling when maximized, with clean expansion of settings panels and options.
  - Custom combobox padding (`28px`) preventing drop-down arrows from overlapping long operation names.
  - User confirmation dialogs on clearing active files or cancelling jobs.
  - Individual file removal button (`Remove Selected`) and keyboard shortcuts (`Delete`, `Backspace`).
- **Batch & Merge Operations**:
  - PDF Merger: Merge multiple PDF documents into a unified output PDF (`pypdf.PdfWriter`).
  - Batch Images to PDF: Multi-page document generation from arbitrary image collections.
  - Batch Images to Animated GIF: Multi-frame sequence merging with frame duration controls.
  - Dedicated "📦 Batch & Merge Tools" workspace grid for 1-click workflow dispatch.
- **Optical Disc & iOS Modern Format Support**:
  - ISO 9660 & Joliet Optical Disc filesystem inspection, extraction, and directory creation (`pycdlib`).
  - Windows native disc burner integration (`isoburn.exe`).
  - Apple iOS `.heic` / `.heif` high-efficiency images with lossless conversion (`pillow-heif`).
  - Apple iOS `.hevc` / H.265 video stream remuxing and transcoding.
- **Pre-Bundled Engine & Model Path Discovery**:
  - Added portable `bin/tesseract/` binary detection in `TesseractDetector` with automatic `TESSDATA_PREFIX` configuration.
  - Added offline `resources/models/whisper/` detection in `SpeechDetector` and `ASREngine`.
  - Added portable LibreOffice search path support in `LibreOfficeDetector`.

## [1.0.0] - 2026-10-11

### Added
- **Application Branding & Icons**:
  - Generated high-resolution rounded-squircle RGBA application icon (`src/omniconvert/resources/icon.png`) and multi-resolution Windows `.ico` (`16x16` through `256x256` at `src/omniconvert/resources/icon.ico`).
  - Integrated taskbar/window icons across `QApplication` (`SetCurrentProcessExplicitAppUserModelID`), `MainWindow`, `HomeView`, and PyInstaller packaging script.
- **Full Document & Office Suite (Offline)**:
  - **PDF to Word (`.pdf` -> `.docx`)** via `pdf2docx`, `PyMuPDF` (`fitz`), and `python-docx` with layout, table, paragraph, and image preservation.
  - **Word to PDF (`.docx` -> `.pdf`)** and bidirectional conversions between `.docx`, `.xlsx`, `.pptx`, `.pdf`, `.txt`, `.html`, `.md`, `.csv`, and `.json` working 100% offline via pure-Python engines (`reportlab`, `python-docx`, `openpyxl`, `python-pptx`, `markdown`) or LibreOffice when installed.
  - **PDF to High-DPI Images (`.png`, `.jpeg`)**, **PDF to HTML**, and **PDF to Markdown** via `PyMuPDF`.
- **Quality & Detail Level Controls**:
  - Added global Quality / Detail Level selector (`Lossless / Exact Quality (100%)`, `High Quality`, `Balanced`, `Compact`, `Custom`) in the Conversion Workspace alongside per-operation parameter schemas.
  - Added `quality=100, subsampling=0 (4:4:4)` lossless-chroma JPEG encoding and `lossless=True` WebP encoding.
- **Comprehensive Audio & Video Support**:
  - Full audio conversions across `mp3`, `wav` (16/24/32-bit PCM), `flac`, `aac`, `m4a` (AAC and Apple Lossless ALAC), `ogg` (Vorbis quality scale), `opus`, and `aiff` with bitrate, sample rate, and channel controls.
  - Video transcoding (`mp4`, `mkv`, `webm`, `mov`, `avi`, `gif`), audio extraction, subtitle extraction, FFprobe metadata-to-JSON, and `data.csv_to_mp4` animated bar-chart video generation.
- **Phase 8 — Archives & Compression (`ArchiveEngine`)**:
  - Added `zip`, `tar`, `tar.gz`/`tgz`, `gz`, and `7z` (`py7zr`) listing, extraction, creation, and cross-format repacking with strict Zip-Slip path traversal protection, symlink blocking, and decompression bomb limits.
- **Phase 9 — Cross-Category Workflow Planner (`WorkflowPlanner` & `WorkflowEngine`)**:
  - Added bounded shortest-path BFS workflow discovery across registered single-step capabilities (e.g., `docx -> txt -> wav`, `mp4 -> wav -> flac`, `png -> txt -> wav`) plus `workflow.archive_to_pdf`.
  - Added per-step intermediate output validation and `WorkflowStepError` reporting.
- **Phase 10 — Local TTS, OCR, ASR & Static Binary Inspection**:
  - Added offline Text-to-Speech (`TTSEngine` via Windows SAPI5 / `pyttsx3` with deterministic PCM WAV fallback), optional local Tesseract OCR (`OCREngine`), optional local Whisper ASR (`ASREngine`), and static binary inspection (`BinaryEngine` for strings, hashes, Shannon entropy, PE headers, and hex dumps).
- **Phase 11–14 — UI Completion, History, Packaging & Verification**:
  - Completed `ConversionWorkspaceView`, `QueueView` (`Open Folder` and `Retry` buttons), persistent `HistoryView`, searchable `FormatExplorerView`, and `SettingsView` with live local dependency & privacy reporting.
  - Added `scripts/check_dependencies.py` and `scripts/build_windows.py` for Windows PyInstaller packaging.
