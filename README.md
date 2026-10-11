# OmniConvert — Universal Windows Desktop File Workspace

<p align="center">
  <img src="src/omniconvert/resources/icon.png" width="140" alt="OmniConvert Icon" />
</p>

<p align="center">
  <strong>Fast, offline-first universal file conversion, extraction, packaging, and inspection for Windows desktop.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg" alt="Windows 10/11">
  <img src="https://img.shields.io/badge/Architecture-x64-success.svg" alt="x64 Architecture">
  <img src="https://img.shields.io/badge/Privacy-100%25%20Offline%20Local-brightgreen.svg" alt="Offline Local">
  <img src="https://img.shields.io/badge/UI-PySide6%20Qt-41CD52.svg" alt="PySide6 Qt">
</p>

---

## 🌟 What is OmniConvert?

**OmniConvert** is an all-in-one Windows desktop application built to eliminate the need for shady online file converters, subscription paywalls, and fragmented single-purpose tools. 

All conversions run **100% locally on your machine**. Your sensitive files, documents, photos, and recordings are never uploaded to the cloud or sent across the internet.

### 🔑 Core Highlights

- **🔒 Local & Private**: Completely offline processing. Zero telemetry on file contents.
- **📄 Full Office & PDF Suite**: Bi-directional conversion between **PDF and Word (.docx)**, Excel (`.xlsx`), PowerPoint (`.pptx`), HTML, Markdown, and TXT without needing Microsoft Office installed.
- **🖼️ Lossless & Precision Quality Presets**: Choose between **Lossless / Exact (100% detail)**, **High Detail**, **Balanced**, or **Compact Size** across images, audio, and video.
- **🎬 Professional Media Engine**: Powered by local FFmpeg 9+ for high-fidelity audio/video transcoding, audio extraction, animated GIF generation, and stream inspection.
- **📦 Protected Archive Engine**: Safe extraction and creation for **ZIP**, **7Z**, **TAR**, and **GZ** with built-in path-traversal safeguards (*Zip Slip* protection) and decompression bomb limits.
- **🔄 Multi-Step Workflow Engine**: Execute chained pipelines such as `Document ➔ Text ➔ Spoken Audio (WAV)`, `Folder/Archive ➔ Merged PDF`, or `CSV ➔ Animated Video Chart`.
- **🔍 Content-Based Sniffing**: Inspects magic bytes and headers rather than blindly trusting file extensions.
- **🎨 Windows-Native UI**: Dark and light themes, drag-and-drop input, real-time background job queue, and searchable format matrix.

---

## 🚀 How to Run and Use OmniConvert

### 1. Launching the App

- **If you downloaded the `.exe` release**: Simply double-click `OmniConvert.exe` to run. No setup or command prompt required!
- **If running from source**: Double-click `run.bat` or run:
  ```powershell
  .\.venv\Scripts\python.exe app.py
  ```

---

### 2. User Guide: How to Convert Files

```
┌──────────────┐     ┌───────────────────────┐     ┌────────────────────────┐     ┌─────────────────────┐
│ 1. Add Files │ ──> │ 2. Choose Operation   │ ──> │ 3. Pick Quality Preset │ ──> │ 4. Start Conversion │
└────────────── economic └───────────────────────┘     └────────────────────────┘     └─────────────────────┘
```

#### Step 1: Add Your Files
- **Drag & Drop**: Drag files or folders directly into the drop zone on the **Home** tab or **Workspace** tab.
- **Browse**: Click **Browse Files** or **+ Add Files** / **+ Add Folder** to select inputs.
- OmniConvert automatically reads the file header and inspects dimensions, streams, codecs, and metadata.

#### Step 2: Choose an Operation
- In the **Workspace** tab, click the **Operation** dropdown. OmniConvert dynamically displays only the valid operations that can be performed on the file.
  - *Example (PDF)*: `Convert PDF to Word (.docx)`, `Extract Text to TXT`, `Export to JSON`, `Extract Page Range`, `Render Pages to PNG`.
  - *Example (DOCX)*: `Convert Document to PDF`, `Convert to Plain Text`, `Export to HTML`, `Convert to Markdown`.
  - *Example (PNG)*: `Convert to JPEG (Lossless / High)`, `Convert to WebP`, `Generate Windows Icon (.ico)`, `Wrap into PDF`.
  - *Example (MP4)*: `Extract Audio to MP3 / WAV / FLAC`, `Convert to Animated GIF`, `Transcode to WebM / MKV`.

#### Step 3: Choose Quality & Fine-Tune Settings
- Use the **Conversion Detail / Quality Preset** selector:
  - **Lossless / Exact**: Disables lossy compression. PNG $\rightarrow$ JPEG uses full `4:4:4` chroma and 100% quality; WebP and AVIF use true mathematical lossless mode; audio uses 24-bit PCM or Apple Lossless (ALAC); video uses `CRF 14`.
  - **High Detail**: Maximum perceptual fidelity with slight compression savings.
  - **Balanced**: Standard default balancing quality and file size.
  - **Compact**: Aggressive compression for small file sizes (great for emails and messaging limits).
- Adjust individual parameters if needed (e.g. custom bitrate, resolution, rotation, sample rate, or background color for transparency flattening).

#### Step 4: Click "Start Conversion"
- The job queues and runs safely in the background. The UI remains fully responsive.
- Monitor live progress in the **Job Queue** tab.
- When finished, click **Open Output Folder** in the **History** tab to locate your new file. Source files are **never overwritten** by default.

---

## 🧩 Supported Formats & Engines

| Category | Supported Formats | Common Operations | Underlying Engine |
|---|---|---|---|
| **Office & Documents** | `DOCX`, `DOC`, `XLSX`, `PPTX`, `ODT`, `RTF` | Word to PDF, Excel to PDF/CSV, PPTX to PDF, Text extraction | `python-docx`, `reportlab`, `openpyxl`, `python-pptx`, LibreOffice |
| **PDF** | `PDF` | PDF to Word (`.docx`), PDF to PNG/JPEG, Extract text, Extract pages, Merge PDFs | `pdf2docx`, `pypdf`, `PyMuPDF` |
| **Images** | `PNG`, `JPEG`, `WEBP`, `AVIF`, `BMP`, `TIFF`, `GIF`, `ICO`, `SVG` | Format conversion, Resize, Rotate, Windows Icon generation, Alpha flattening | `Pillow`, `pillow-avif-plugin`, `svglib`, `reportlab` |
| **Audio** | `WAV`, `MP3`, `FLAC`, `AAC`, `M4A (AAC/ALAC)`, `OGG`, `Opus`, `AIFF` | Transcoding, Bit depth conversion (16/24-bit), Sample rate adjustment | `FFmpeg` 9+ |
| **Video** | `MP4`, `MKV`, `WEBM`, `MOV`, `AVI` | Video transcoding, Audio extraction, Animated GIF extraction, Subtitle extraction | `FFmpeg` 9+ |
| **Archives** | `ZIP`, `7Z`, `TAR`, `GZ` | Safe extraction, Compression, Multi-format packaging, Path traversal defense | Built-in `zipfile`, `tarfile`, `py7zr` |
| **Structured Data** | `JSON`, `CSV`, `YAML`, `XML` | Bidirectional conversions, Schema flattening, XXE-protected parsing | Python stdlib, `pyyaml`, `defusedxml` |
| **Text & Code** | `TXT`, `MD`, `HTML`, `LOG`, Source files | CRLF $\leftrightarrow$ LF line ending conversion, UTF-8 / UTF-16 / ASCII encoding | Built-in Text Engine |
| **Speech (TTS & ASR)** | `TXT`, `DOCX`, `PDF` $\rightarrow$ `WAV`; `Audio` $\rightarrow$ `TXT` | Local Text-to-Speech (offline Windows SAPI5) & Optional Speech Recognition | Windows SAPI5 / pyttsx3, `faster-whisper` |
| **Binary Inspection** | `EXE`, `DLL`, `BIN`, Raw files | Cryptographic hashes (SHA-256, MD5), Printable strings extraction, Hex dump | Built-in Static Engine |

---

## ⚡ Optional Local Engines: How to Enable OCR & Speech-to-Text

OmniConvert works out-of-the-box for **69 operations**. Two optional operations require external offline packages if you want them enabled:

### 1. Enable Image OCR (`Extract Text from Image (OCR)`)
OmniConvert uses the open-source **Tesseract OCR** engine for offline image text extraction.
- **How to enable**:
  Open PowerShell as Administrator and run:
  ```powershell
  winget install UB-Mannheim.TesseractOCR
  ```
  *Restart OmniConvert. The app will detect `tesseract.exe` automatically and activate OCR.*

### 2. Enable Audio-to-Text (`Transcribe Audio (Speech Recognition)`)
OmniConvert uses **faster-whisper** for offline neural speech transcription.
- **How to enable**:
  In your OmniConvert environment, run:
  ```powershell
  pip install faster-whisper
  ```
  *Restart OmniConvert. The app will detect the library and download small local weights on first run without calling any external APIs.*

---

## 🛠️ Building Standalone `.exe` for Windows

OmniConvert includes a pre-configured PyInstaller build script with embedded assets, custom icon, and hidden imports:

```powershell
# 1. Activate environment
.\.venv\Scripts\Activate.ps1

# 2. Build standalone Windows executable
python scripts/build_windows.py
```

The resulting portable executable will be placed in `dist/OmniConvert/OmniConvert.exe`.

---

## 📄 License

OmniConvert is released under the **[MIT License](LICENSE)**. Free to use, modify, and distribute for personal and commercial projects.
