# Changelog

All notable changes to **OmniConvert** are documented in this file.

## [Unreleased] - Phase 17 & Phase 18
### Planned
- **Phase 17 — Application Polish & UX Refinement**:
  - Refined Qt styling, visual drag-and-drop hover feedback, and enhanced tooltips for quality presets (Lossless, High, Balanced, Compact).
  - Double-click to open converted files in History.
  - Confirmation dialogs for clearing active queues and workspace files.
- **Phase 18 — Multi-Tier Distribution & Smart Installer**:
  - Inno Setup installer (`OmniConvert-Setup.exe`) with on-demand component selection (OCR & Whisper).
  - 4 portable editions hosted on GitHub Releases (`Lite`, `OCR`, `Whisper`, `Full`).

## [1.1.0] - 2026-10-12
### Added
- **ISO 9660 & Joliet Optical Disc Engine (`pycdlib`)**:
  - Full support for `.iso` image files: inspect volume descriptors, safely extract archive/disc contents, create ISO 9660 / Joliet filesystem images from directories, and cross-repack between `.iso` and `.zip`/`.7z`/`.tar`.
  - Added native Windows optical disc burner launch integration (`isoburn.exe`).
- **Apple iOS HEIC & HEVC Integration**:
  - Added `.heic` / `.heif` high-efficiency image support with lossless conversion via `pillow-heif`.
  - Added `.hevc` / H.265 video stream remuxing and transcoding via FFmpeg.
- **Batch Image Tools & Extended Workspace Controls**:
  - Added batch multi-image to single multi-page PDF (`image.batch_to_pdf`).
  - Added batch multi-image to animated GIF (`image.batch_to_gif`).
  - Added granular "Remove Selected" button and keyboard shortcuts (`Delete`, `Backspace`) in the Conversion Workspace.
  - Added "Clear All" and "Clear Finished" queue actions in the Job Queue.

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
