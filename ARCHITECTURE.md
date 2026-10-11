# OmniConvert — Technical Architecture

OmniConvert is a **local-first Windows desktop application** built with Python 3.11+ and PySide6 (Qt 6). All file inspection, single-step conversion, and multi-step workflow orchestration execute strictly on the user's machine without network calls or telemetry.

---

## 1. Layered System Overview

```text
+-------------------------------------------------------------------+
|                        Presentation Layer                         |
|   MainWindow | HomeView | ConversionWorkspaceView | QueueView     |
|   HistoryView | FormatExplorerView | SettingsView | Theme (QSS)   |
+-------------------------------------------------------------------+
                                  |
                         Qt Signals & Slots
                                  v
+-------------------------------------------------------------------+
|                    Application & Core Services                    |
|   FileDetector (Magic Bytes + MIME) | CapabilityRegistry          |
|   WorkflowPlanner (Bounded BFS)     | JobManager (QThreadPool)    |
|   HistoryManager (Local JSON)       | AppSettings                 |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    Execution & Safety Layer                       |
|   SafeSubprocessRunner (Arg Arrays, Cancellation, Timeout)        |
|   JobWorkspace (Isolated Temp Dir + Atomic Promotion)             |
|   OutputValidator (Format-Specific Structural Verification)       |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                       Pluggable Engines                           |
|   ImageEngine (Pillow + PyMuPDF) | PDFEngine (pypdf + pdf2docx)   |
|   OfficeEngine (docx/openpyxl/pptx/reportlab + LibreOffice)       |
|   FFmpegEngine (ffmpeg/ffprobe)  | DataEngine (json/yaml/xml/csv) |
|   ArchiveEngine (zip/tar/gz/7z)  | TTSEngine / OCREngine / Binary |
+-------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 File Inspection (`src/omniconvert/core/file_detector.py`)
- Inspects magic bytes (PNG, JPEG, GIF, WebP, BMP, TIFF, ICO, PDF, ZIP/DOCX/XLSX/PPTX, 7Z, GZ, TAR, MP3/ID3, WAV/RIFF, FLAC, OGG, MP4/ISO-BMFF, MKV/EBML, MZ/PE) before falling back to extension and MIME heuristics.
- Differentiates Office Open XML containers (`.docx`, `.xlsx`, `.pptx`) from generic `.zip` archives by inspecting internal zip entries (`word/document.xml`, `xl/workbook.xml`, `ppt/presentation.xml`).

### 2.2 Capability Registry (`src/omniconvert/core/registry.py`)
- Central source of truth for all supported operations (`Capability` dataclass).
- Automatically probes installed local engines at startup (`pillow`, `pypdf`, `libreoffice`, `ffmpeg`, `data`, `archive`, `tts`, `ocr`, `asr`, `binary`, `workflow`).
- Filters operations dynamically by source format and runtime stream availability (e.g. hiding subtitle extraction on videos without subtitle tracks, and hiding audio extraction on silent videos).

### 2.3 Multi-Step Workflow Planner (`src/omniconvert/core/planner.py`)
- Uses bounded, cycle-free Breadth-First Search (BFS) over registered capabilities to discover multi-step cross-category pipelines (e.g., `DOCX -> TXT -> WAV`, `PNG -> PDF -> DOCX`).
- Prevents nonsensical intermediate archive hops (e.g. packaging into `.zip` mid-pipeline when the final target is not an archive).
- Executes each step inside an isolated `step_N` subdirectory, validates intermediate outputs via `validate_output`, and cleans up intermediate artifacts in a `finally` block.

### 2.4 Asynchronous Job Queue & Atomic Promotion (`src/omniconvert/core/job_manager.py`, `src/omniconvert/core/temp_files.py`)
- Runs conversions on background worker threads via `QThreadPool` (`JobWorker`), keeping the Qt GUI responsive.
- Every job writes to an isolated scratch workspace (`%LOCALAPPDATA%\OmniConvert\Temp\job_<id>_<rand>`).
- Output files are validated by `validate_output` (`src/omniconvert/core/validation.py`) before being promoted to the user's destination directory, guaranteeing that failed or cancelled jobs never overwrite or corrupt source files.

### 2.5 Security Guardrails
- **Subprocess Safety (`src/omniconvert/core/safe_subprocess.py`)**: Never invokes a shell (`shell=False`), passes argument lists directly, hides console windows on Windows (`CREATE_NO_WINDOW`), and polls `is_cancelled()` every 50 ms so user cancellation immediately kills child processes.
- **Archive Hardening (`src/omniconvert/engines/archive_engine.py`)**: Pre-scans all archive manifests before extraction to block Zip-Slip (`../`, absolute paths, drive-letter escapes), reject symlinks/hardlinks, and enforce uncompressed size (`2 GB`) and compression ratio (`200:1`) limits.
- **XML Hardening (`src/omniconvert/engines/data_engine.py`)**: Uses `defusedxml` to block XXE and entity expansion attacks.
- **Static Binary Inspection (`src/omniconvert/engines/binary_engine.py`)**: Computes cryptographic hashes, Shannon entropy, printable strings, and static PE header metadata without ever executing or emulating binary inputs.
